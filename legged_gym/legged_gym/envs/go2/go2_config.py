"""Go2 morphology with the existing HIMLoco Go1 task and HIM/PPO defaults."""

from legged_gym.envs.go1.go1_config import Go1RoughCfg, Go1RoughCfgPPO


class Go2RoughCfg(Go1RoughCfg):
    class control(Go1RoughCfg.control):
        stiffness = {'joint': 20.0}
        damping = {'joint': 0.5}

    class asset(Go1RoughCfg.asset):
        file = '{LEGGED_GYM_ROOT_DIR}/resources/robots/go2/urdf/go2.urdf'
        name = 'go2'


class Go2RoughCfgPPO(Go1RoughCfgPPO):
    class runner(Go1RoughCfgPPO.runner):
        experiment_name = 'rough_go2'
