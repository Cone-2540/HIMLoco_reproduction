#!/usr/bin/env python3
"""Finish paired selection, reserved-seed transfer checks, recordings and archive."""
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

ROOT=Path(__file__).resolve().parents[1]
LOG=Path.home()/'robotics/logs'
PY=Path.home()/'robotics/envs/himloco-mujoco-py311/bin/python'
DEADLINE=datetime.fromisoformat('2026-10-14T07:20:00+08:00')


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):return json.loads(Path(path).read_text())
def save(path,data):Path(path).write_text(json.dumps(data,indent=2)+'\n')
def run(command,log,env=None):
    if datetime.now().astimezone()>=DEADLINE:raise RuntimeError('Deadline reached')
    print('RUN '+str(log),flush=True)
    with Path(log).open('w') as out:
        subprocess.run([str(x) for x in command],cwd=ROOT,stdout=out,stderr=subprocess.STDOUT,check=True,env=env,
                       timeout=min(1800,max(1,(DEADLINE-datetime.now().astimezone()).total_seconds())))


def matrix(policy,config,name,suite,seeds,seed_start):
    directory=LOG/name
    if not (directory/'matrix.json').is_file():
        run([PY,ROOT/'sim2sim/matrix.py','--policy',policy,'--config',config,'--output',directory,
             '--suite',suite,'--seeds',str(seeds),'--seed-start',str(seed_start)],LOG/(name+'-console.txt'))
    result=read(directory/'matrix.json')
    shutil.copyfile(directory/'matrix.json',ROOT/'reproduction'/(name+'.json'))
    return result


def main():
    while not (ROOT/'reproduction/night3-contact-arm3-launch.json').exists():
        if datetime.now().astimezone()>=DEADLINE:raise RuntimeError('Deadline reached while waiting for GPU jobs')
        time.sleep(10)
    arm3=read(ROOT/'reproduction/night3-contact-arm3-launch.json')
    if arm3['exit_code']!=0:raise RuntimeError('Contact arm did not exit cleanly')
    print('GPU training complete; freezing and validating candidates',flush=True)
    original=ROOT/'artifacts/go2-stairs-night2-faithful-seed1213-760'
    sources=[('baseline',original,[760]),
             ('arm1',ROOT/'isaaclab/logs/2026-10-14_01-01-31_night3-robust-faithful-arm1',[820,840,860]),
             ('arm2',ROOT/'isaaclab/logs/2026-10-14_01-29-50_night3-deployment-mixed-arm2',[860,920,960]),
             ('arm3',Path(arm3['simulator_log_dir']),[900,960,1020,1060])]
    candidates=[]
    for label,source,iterations in sources:
        for iteration in iterations:
            output=ROOT/'artifacts'/f'go2-night3-frozen-{label}-{iteration}'
            output.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(source/'config.json',output/'config.json')
            if not (output/'policy.pt').exists():
                run([PY,ROOT/'sim2sim/export.py',source/f'model_{iteration}.pt','--config',output/'config.json',
                     '--output',output/'policy.pt'],LOG/f'night3-export-{label}-{iteration}.txt')
            result=matrix(output/'policy.pt',output/'config.json',f'night3-v2-selection-{label}-{iteration}','deployment',8,1400)
            standards=result['summary'][:6]
            standard_pass=sum(x['passed'] for x in standards)
            contacts=sum(x['mean_calf_loaded_contact_fraction'] for x in standards[2:])/4
            c={'label':label,'iteration':iteration,'source':str(source),'artifact':str(output),
               'passed':result['passed'],'total':result['total'],'standard_pass':standard_pass,'standard_total':48,
               'stairs_loaded_contact_fraction':contacts,'policy_sha256':digest(output/'policy.pt')}
            candidates.append(c)
            save(ROOT/'reproduction/night3-v2-selection.json',{'development_seeds':[1400,1407],'candidates':candidates})
            print('SELECTION '+json.dumps(c),flush=True)
    # Whole-flight completion first; among equally complete candidates, prefer
    # lower loaded leg contact. All candidates used the same final evaluator.
    selected=max(candidates,key=lambda c:(c['standard_pass'],c['passed'],-c['stairs_loaded_contact_fraction']))
    frozen=ROOT/'artifacts/go2-night3-selected'
    frozen.mkdir(parents=True,exist_ok=True)
    source=Path(selected['source']);artifact=Path(selected['artifact'])
    for file in ['config.json','policy.pt']:shutil.copyfile(artifact/file,frozen/file)
    shutil.copyfile(source/f"model_{selected['iteration']}.pt",frozen/'model.pt')
    for file in ['result.json','domain-parameters-initial.json','domain-parameters-final.json']:
        if (source/file).exists():shutil.copyfile(source/file,frozen/file)
    freeze={'selected':selected,'criterion':'standard flight completion, overall deployment completion, then loaded stair leg contact',
            'frozen_local':datetime.now().astimezone().isoformat(),'reserved_seeds_start':1800,
            'policy_sha256':digest(frozen/'policy.pt'),'checkpoint_sha256':digest(frozen/'model.pt'),
            'runner_sha256':digest(ROOT/'sim2sim/run.py'),'candidate_results':candidates}
    freeze_path=ROOT/'reproduction/night3-selection-frozen.json'
    if freeze_path.exists():
        previous=read(freeze_path)
        if previous['policy_sha256']!=freeze['policy_sha256']:raise RuntimeError('Frozen selection must not change after final seeds are opened')
        freeze=previous
    else:
        save(freeze_path,freeze)
    results={}
    for label,policy,config in [('baseline',original/'policy.pt',original/'config.json'),
                               ('selected',frozen/'policy.pt',frozen/'config.json')]:
        results[label]={}
        for suite,seeds in [('nominal',24),('deployment',24)]:
            results[label][suite]=matrix(policy,config,f'night3-final-{label}-{suite}',suite,seeds,1800)
        directory=LOG/f'night3-final-{label}-flat8'
        if not (directory/'matrix.json').exists():
            run([PY,ROOT/'sim2sim/flat_matrix.py','--policy',policy,'--config',config,'--output',directory,
                 '--seed-start','1800','--seeds','8'],LOG/f'night3-final-{label}-flat8-console.txt')
        results[label]['flat8']=read(directory/'matrix.json')
        shutil.copyfile(directory/'matrix.json',ROOT/'reproduction'/f'night3-final-{label}-flat8.json')
    gpu=[]
    for name,terrain,extra in [
        ('night3-final-isaac-nominal','stairs',['--stair_batch','reproduction/night3-isaac-paper-stair-batch.json']),
        ('night3-final-isaac-deployment','stairs',['--stair_batch','reproduction/night3-isaac-paper-stair-batch.json','--domain_profile','deployment','--eval_dynamics']),
        ('night3-final-isaac-flat','flat',['--warm_start','reset'])]:
        args=['python3',ROOT/'reproduction/run-night3-job.py','--name',name,'--max-seconds','900','--',
              'evaluate','--terrain',terrain,'--reward_profile','faithful','--num_envs','512',
              '--checkpoint',original/'model_760.pt','--candidate_checkpoint',frozen/'model.pt',
              '--seed','1800','--eval_seconds','25' if terrain=='stairs' else '20',*extra]
        if terrain=='stairs':args+=['--eval_seed','1800','--eval_seed','1801','--eval_randomized','--speed','.3']
        try:run(args,LOG/(name+'-console.txt'))
        except subprocess.CalledProcessError as error:print(f'GPU validation exited {error.returncode}; retained logs',flush=True)
        wrapper=list(LOG.glob('*_'+name+'/launch-record.json'))
        if wrapper:
            record=read(wrapper[-1]);gpu.append(record)
            shutil.copyfile(wrapper[-1],ROOT/'reproduction'/(name+'-launch.json'))
            path=Path(record.get('simulator_log_dir','/nonexistent'))
            if (path/'result.json').exists():
                shutil.copyfile(path/'result.json',ROOT/'reproduction'/(name+'-result.json'))
                for result in path.glob('candidates/*/result.json'):
                    shutil.copyfile(result,ROOT/'reproduction'/(name+'-selected-result.json'))
    videos=[]
    for terrain in ['flat','asc','desc']:
        directory=LOG/f'night3-selected-video-{terrain}'
        if not (directory/'result.json').exists():
            args=[PY,ROOT/'sim2sim/run.py','--policy',frozen/'policy.pt','--config',frozen/'config.json',
                  '--output',directory,'--terrain',terrain,'--seconds','25','--seed','1800','--video']
            if terrain!='flat':args+=['--heading-feedback']
            environment=dict(os.environ,MUJOCO_GL='egl');run(args,LOG/f'night3-selected-video-{terrain}-console.txt',environment)
        r=read(directory/'result.json');videos.append({'terrain':terrain,'video':str(directory/'video.mp4'),'result':r})
    save(ROOT/'reproduction/night3-selected-video-manifest.json',videos)
    initial=read(ROOT/'reproduction/night3-driver-initial-20261014.json')
    driver={path:{'initial':value['sha256'],'final':digest(path),'unchanged':digest(path)==value['sha256']}
            for path,value in initial['files'].items()}
    save(ROOT/'reproduction/night3-driver-final-20261014.json',{'recorded_local':datetime.now().astimezone().isoformat(),'files':driver,
         'all_unchanged':all(v['unchanged'] for v in driver.values())})
    peak=0
    for csv in LOG.glob('*_night3-*/gpu-resource.csv'):
        for line in csv.read_text().splitlines()[1:]:
            try:peak=max(peak,float(line.split(',')[3]))
            except (IndexError,ValueError):pass
    overview={'selected':selected,'frozen':freeze,'final_mujoco':{label:{suite:{'passed':r['passed'],'total':r['total'],'summary':r['summary']}
              for suite,r in suites.items()} for label,suites in results.items()},'gpu_jobs':gpu,'videos':videos,
              'peak_total_gpu_mib':peak,'driver_unchanged':all(v['unchanged'] for v in driver.values()),
              'finished_local':datetime.now().astimezone().isoformat(),'hardware_test_performed':False}
    save(ROOT/'reproduction/night3-final-overview.json',overview)
    lines=['# 2026-10-14：MuJoCo sim2sim 与域随机化',
           '',f"完成时间：{overview['finished_local']}。没有向实物发送控制指令。",'',
           'MuJoCo 3.3.7 独立安装在 `/home/cone/robotics/envs/himloco-mujoco-py311`，Go2 官方模型在共享 assets 目录；Isaac Lab 继续使用既有容器。',
           '',f"冻结候选：**{selected['label']} / {selected['iteration']}**，`artifacts/go2-night3-selected/`；策略 SHA256 `{freeze['policy_sha256']}`。",'',
           '候选先用 1400–1407 开发种子按标准楼梯完成率、全部域扰动完成率、受力小腿接触选定；以下 1800 起的种子不参与训练或候选选择。',
           '', '| 策略 | 名义前进/楼梯 | 独立域扰动+多种楼梯 | 完整20秒八类运动 |','| --- | --- | --- | --- |']
    for label in ['baseline','selected']:
        rr=results[label];lines.append('| '+label+' | '+' | '.join(f"{rr[s]['passed']}/{rr[s]['total']}" for s in ['nominal','deployment','flat8'])+' |')
    lines+=['','训练保留原 HIM/HIMPPO、6×45 历史和原 actor 输入，地形扫描只供 critic。',
            'Arm1：原奖励+robust 域，100 次更新。Arm2：原奖励+deployment 域、25% 多方向平地、探索标准差0.3，200次更新。Arm3：Arm1基础上 deployment 域+原有轻接触惩罚 -0.02，200次更新，是显式 Go2 奖励适配。',
            '', '原模型已包含质量和重心变化。本次实际验证并训练足端材料、较大重心范围、独立 PD 增益，并新增每次重置的关节电机强度0.9–1.1、位置指令延迟0–10ms。物理参数初末读回、优化器/算法配置、所有候选及失败结果均保留。',
            '', 'MuJoCo 控制接口按名称映射关节，200Hz PD/50Hz策略，动作默认位置+0.25×输出，DC速度–扭矩曲线与训练一致。角速度从世界坐标转换到机身，避免误用惯性主轴局部坐标；随机惯性参数重算，状态时间同步。',
            '', '通过的 MuJoCo 模型将 Menagerie 原关节阻尼2、摩擦损失0.2、armature0.01对齐到训练值0，保留橡胶足端接触与全部腿部碰撞。原策略在未对齐的默认模型下未通过；不能宣称任意 Go2 模型均可迁移。',
            '', '楼梯成功需要四足越过最后踏步并直立、无机身接触保持0.5秒，不能靠自动重置或到中段算成功。含外部航向反馈，不能宣称为零航向指令结果。接触同时统计几何接触与>1N实际受力，不把完成率等同于丝滑步态。',
            '', '| 最终候选测试场景 | 成功 | 受力小腿接触比例 | 小腿最大法向力N |','| --- | --- | --- | --- |']
    for row in results['selected']['deployment']['summary']:
        lines.append(f"| {row['case']} | {row['passed']}/{row['total']} | {row['mean_calf_loaded_contact_fraction']:.1%} | {row['maximum_calf_normal_force_n']:.1f} |")
    lines+=['', 'Isaac Lab 已进行配对名义楼梯、deployment 域楼梯与平地检查，原始结果位于 `night3-final-isaac-*-result.json` 和对应 selected-result；程序退出成功与性能验收分开记录。',
            '',f"整机 GPU 峰值 {peak/1024:.2f} GiB。五个驱动/图形配置基准文件哈希全部一致：{overview['driver_unchanged']}。",'',
            '下午部署需依据真实 EDU 的关节顺序、IMU坐标、控制频率和减速比核对控制协议。先验证悬吊与低速平地；八类运动或楼梯域测试未通过的能力不应直接开放。sim2sim成功不能替代实物验证，也不能把残留受力小腿接触认定为已实现丝滑上下楼梯。',
            '', '录像：']
    for video in videos:lines.append(f"- {video['terrain']}：`{video['video']}`")
    lines+=['','运行说明见 `sim2sim/README_zh.md`；完整结论与来源见 `night3-final-overview.json`。']
    (ROOT/'reproduction/night3-report_zh.md').write_text('\n'.join(lines)+'\n')
    print('CLOSEOUT_COMPLETE '+json.dumps({'selected':selected,'results':overview['final_mujoco'],'finished':overview['finished_local']}),flush=True)


if __name__=='__main__':main()
