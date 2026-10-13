import unittest
import tempfile
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import mujoco
from run import ASSETS, DEFAULT_POLICY, dc_torque, observation, push_history, make_model
import json


class InterfaceTests(unittest.TestCase):
    def test_observation_scaling_and_history(self):
        default = np.arange(12.)
        frame = observation([.5,-.2,.8],np.array([1.,2,3]),np.array([0.,0,-1]),
                            default+.1,np.ones(12)*2,default,np.ones(12)*.3)
        np.testing.assert_allclose(frame[:9],[1,-.4,.2,.25,.5,.75,0,0,-1])
        np.testing.assert_allclose(frame[9:21],.1)
        np.testing.assert_allclose(frame[21:33],.1)
        np.testing.assert_allclose(frame[33:],.3)
        history=np.zeros(270,np.float32)
        for i in range(8): history=push_history(history,np.ones(45)*i)
        np.testing.assert_equal(history.reshape(6,45)[:,0],[7,6,5,4,3,2])

    def test_speed_curve_brakes_at_overspeed(self):
        speed=np.array([-90.,-30.1,0.,30.1,90.])
        effort=np.ones(5)*23.7
        tau,_=dc_torque(np.ones(5)*100,np.zeros(5),speed,25,.5,effort,np.ones(5)*30.1)
        np.testing.assert_allclose(tau,[23.7,23.7,23.7,0,-23.7])
        tau,_=dc_torque(np.ones(5)*-100,np.zeros(5),speed,25,.5,effort,np.ones(5)*30.1)
        np.testing.assert_allclose(tau,[23.7,0,-23.7,-23.7,-23.7])

    def test_model_mapping_and_body_angular_velocity(self):
        args=SimpleNamespace(assets=ASSETS,dt=.005,stock_joint_physics=False,
            contact_profile='menagerie',terrain='flat',steps=6,depth=.27,width=1.2,
            height=.16,nosing=0,friction=1.,mass_scale=1.,com_offset=[0,0,0])
        with tempfile.TemporaryDirectory() as directory:
            model,base,_,_=make_model(args,Path(directory))
            names=json.loads((DEFAULT_POLICY.parent/'config.json').read_text())['joint_names']
            js=[mujoco.mj_name2id(model,mujoco.mjtObj.mjOBJ_JOINT,n) for n in names]
            self.assertEqual(len(set(js)),12)
            self.assertTrue(all(j>=0 for j in js))
            aids=[np.flatnonzero(model.actuator_trnid[:,0]==j).item() for j in js]
            self.assertEqual(aids,[0,3,6,9,1,4,7,10,2,5,8,11])
            data=mujoco.MjData(model)
            # Nontrivial body rotation: pitch pi/2 maps down to body +X.
            data.qpos[3:7]=[np.sqrt(.5),0,np.sqrt(.5),0]
            data.qvel[3:6]=[.2,-.3,.4]
            mujoco.mj_forward(model,data)
            R=data.xmat[base].reshape(3,3)
            np.testing.assert_allclose(R.T@np.array([0,0,-1]),[1,0,0],atol=1e-12)
            velocity=np.zeros(6)
            mujoco.mj_objectVelocity(model,data,mujoco.mjtObj.mjOBJ_BODY,base,velocity,0)
            np.testing.assert_allclose(R.T@velocity[:3],data.qvel[3:6],atol=1e-12)
            mujoco.mj_objectVelocity(model,data,mujoco.mjtObj.mjOBJ_BODY,base,velocity,1)
            self.assertFalse(np.allclose(velocity[:3],data.qvel[3:6]))
            feet=[mujoco.mj_name2id(model,mujoco.mjtObj.mjOBJ_GEOM,n) for n in ('FL','FR','RL','RR')]
            self.assertTrue(all(model.geom_contype[g]==1 and model.geom_conaffinity[g]==2 for g in feet))

    def test_real_tread_heights_and_thin_overhangs(self):
        args=SimpleNamespace(assets=ASSETS,dt=.005,stock_joint_physics=False,
            contact_profile='menagerie',terrain='asc',steps=6,depth=.27,width=1.2,
            height=.16,nosing=.02,friction=1.,mass_scale=1.,com_offset=[0,0,0])
        def height(model,data,x):
            distance=mujoco.mj_ray(model,data,np.array([x,.5,3.]),np.array([0.,0.,-1.]),
                None,1,-1,np.array([-1],dtype=np.int32))
            return 3-distance
        with tempfile.TemporaryDirectory() as directory:
            model,_,start,_=make_model(args,Path(directory));data=mujoco.MjData(model);mujoco.mj_forward(model,data)
            for i in range(6):
                self.assertAlmostEqual(height(model,data,start+(i+.5)*.27),(i+1)*.16)
            self.assertAlmostEqual(height(model,data,start-.01),.16)
            self.assertAlmostEqual(height(model,data,start-.03),0.)
            nose=mujoco.mj_name2id(model,mujoco.mjtObj.mjOBJ_GEOM,'nosing_0')
            self.assertAlmostEqual(model.geom_size[nose,2],.015)
            args.terrain='desc'
            model,_,start,_=make_model(args,Path(directory));data=mujoco.MjData(model);mujoco.mj_forward(model,data)
            for i in range(5):
                self.assertAlmostEqual(height(model,data,start+(i+.5)*.27),(5-i)*.16)
            self.assertAlmostEqual(height(model,data,start+.01),.96)
            self.assertAlmostEqual(height(model,data,start+.03),.8)


if __name__=='__main__':unittest.main()
