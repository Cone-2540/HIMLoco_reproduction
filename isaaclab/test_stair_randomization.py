"""CPU configuration checks against the pinned Lab 3 public manager APIs."""

import copy
import json
import unittest
from types import SimpleNamespace as NS

from isaaclab.actuators import DCMotorCfg

from stair_randomization import (_domain_terrain_material, capture_domain_parameters,
                                 configure_conservative_calf_limits, configure_stair_randomization)


def config():
    robot = NS(actuators={"base_legs": DCMotorCfg(
        joint_names_expr=[".*_hip_joint", ".*_thigh_joint", ".*_calf_joint"],
        actuator_effort_limit={".*_hip_joint": 23.7, ".*_thigh_joint": 23.7, ".*_calf_joint": 45.43},
        saturation_effort={".*_hip_joint": 23.7, ".*_thigh_joint": 23.7, ".*_calf_joint": 45.43},
        actuator_velocity_limit={".*_hip_joint": 30.1, ".*_thigh_joint": 30.1, ".*_calf_joint": 15.70},
        stiffness=25., damping=.5,
    )})
    return NS(scene=NS(robot=robot, terrain=NS(physics_material=NS(
        static_friction=1., dynamic_friction=1., friction_combine_mode="multiply"))),
        sim=NS(use_newton_actuators=False), events=NS(
            physics_material=NS(params={}), base_com=NS(params={}),
            add_base_mass=NS(mode="startup", params={
                "mass_distribution_params": (.8, 1.25), "operation": "scale",
                "distribution": "log_uniform", "recompute_inertia": True})))


class StairRandomizationTest(unittest.TestCase):
    def test_basic_changes_only_feet_material_and_small_com_and_retains_mass(self):
        cfg = config()
        mass, motor = cfg.events.add_base_mass, cfg.scene.robot.actuators["base_legs"]
        report = configure_stair_randomization(cfg, "basic")
        material = cfg.events.physics_material
        self.assertEqual(material.mode, "startup")
        self.assertEqual(material.params["asset_cfg"].body_names, ".*_foot")
        self.assertTrue(material.params["make_consistent"])
        self.assertEqual(material.params["dynamic_friction_range"], (.5, 1.))
        self.assertEqual(cfg.events.base_com.params["com_range"]["x"], (-.01, .01))
        self.assertIs(cfg.events.add_base_mass, mass)
        self.assertIs(cfg.scene.robot.actuators["base_legs"], motor)
        self.assertIsNone(cfg.events.him_actuator_gains)
        self.assertTrue(report["base_mass"]["preserved"])
        self.assertFalse(report["action_delay_randomization"])
        self.assertFalse(report["motor_strength_randomization"])

    def test_robust_uses_supported_reset_gain_randomizer_and_larger_com(self):
        cfg = config()
        report = configure_stair_randomization(cfg, "robust")
        gain = cfg.events.him_actuator_gains
        self.assertEqual(gain.func, "isaaclab.envs.mdp:randomize_actuator_gains")
        self.assertEqual(gain.mode, "reset")
        self.assertEqual(gain.params["operation"], "scale")
        self.assertEqual(gain.params["stiffness_distribution_params"], (.9, 1.1))
        self.assertEqual(cfg.events.base_com.params["com_range"], {
            "x": (-.03, .03), "y": (-.02, .02), "z": (-.01, .01)})
        self.assertEqual(report["pd_gain_scale"], [.9, 1.1])

    def test_none_and_invalid_profile_do_not_mutate_events(self):
        cfg = config()
        before = copy.copy(vars(cfg.events))
        self.assertTrue(configure_stair_randomization(cfg, "none")["events_unchanged"])
        self.assertEqual(vars(cfg.events), before)
        with self.assertRaisesRegex(ValueError, "domain profile"):
            configure_stair_randomization(cfg, "unrecognized")
        self.assertEqual(vars(cfg.events), before)

    def test_native_backend_rejected_before_any_configuration_changes(self):
        cfg = config()
        cfg.sim.use_newton_actuators = True
        material = cfg.events.physics_material
        with self.assertRaisesRegex(ValueError, "native Newton"):
            configure_stair_randomization(cfg, "robust")
        self.assertIs(cfg.events.physics_material, material)

    def test_conservative_knee_limits_copy_motor_and_preserve_other_joints(self):
        cfg = config()
        original = cfg.scene.robot.actuators["base_legs"]
        report = configure_conservative_calf_limits(cfg)
        actual = cfg.scene.robot.actuators["base_legs"]
        self.assertIsNot(actual, original)
        self.assertEqual(original.actuator_effort_limit[".*_calf_joint"], 45.43)
        self.assertEqual(actual.actuator_effort_limit[".*_calf_joint"], 35.55)
        self.assertEqual(actual.saturation_effort[".*_calf_joint"], 35.55)
        self.assertEqual(actual.actuator_velocity_limit[".*_calf_joint"], 20.07)
        self.assertEqual(actual.joint_velocity_limit, actual.actuator_velocity_limit)
        self.assertEqual(actual.joint_effort_limit, actual.actuator_effort_limit)
        self.assertEqual(actual.actuator_effort_limit[".*_hip_joint"], 23.7)
        self.assertEqual(actual.actuator_velocity_limit[".*_thigh_joint"], 30.1)
        self.assertEqual(actual.stiffness, 25.)
        self.assertLess(abs(report["motor_power_product_W"] / report["previous_motor_power_product_W"] - 1), .001)

    def test_conservative_knee_test_rejects_training(self):
        cfg = config()
        motor = cfg.scene.robot.actuators["base_legs"]
        with self.assertRaisesRegex(ValueError, "evaluation/play only"):
            configure_conservative_calf_limits(cfg, "train")
        self.assertIs(cfg.scene.robot.actuators["base_legs"], motor)


class DomainReadbackTest(unittest.TestCase):
    """Real CPU event/actuator objects with a fake physics readback boundary."""

    def fixture(self, randomized=True):
        import torch
        import warp as wp
        from isaaclab.actuators import DCMotor
        from isaaclab.envs.mdp import randomize_actuator_gains, randomize_rigid_body_com, randomize_rigid_body_mass

        wp.init()
        cfg = config()
        configure_stair_randomization(cfg, "robust")
        names = [leg + "_" + joint + "_joint" for joint in ("hip", "thigh", "calf")
                 for leg in ("FL", "FR", "RL", "RR")]
        motor = DCMotor(cfg.scene.robot.actuators["base_legs"], names, slice(None), 8, "cpu")
        body_names = ["base", "FL_foot", "FR_foot", "RL_foot", "RR_foot"]
        mapping = [2, 4, 0, 3, 1]
        masses = torch.full((8, 5), .1)
        masses[:, 0] = 6.0
        inertias = torch.eye(3).reshape(1, 1, 9).repeat(8, 5, 1) * .02
        com = torch.zeros(8, 5, 7)
        com[..., -1] = 1
        materials = torch.tensor([.8, .7, 0.]).repeat(8, 5, 1)
        materials[:, 2] = torch.tensor([2., 1.5, 0.])  # Base shape in backend order.
        root_view = NS(max_shapes=5, link_paths=[["link" + str(i) for i in range(5)]],
                       get_material_properties=lambda: wp.from_torch(materials))
        robot = NS(body_names=body_names, num_bodies=5, num_joints=12, device="cpu",
                   actuators={"base_legs": motor}, root_view=root_view,
                   map_body_ids_to_backend=lambda ids: [mapping[i] for i in ids],
                   _physics_sim_view=NS(create_rigid_body_view=lambda path: NS(max_shapes=1)),
                   data=NS(body_mass=NS(torch=masses), body_inertia=NS(torch=inertias),
                           body_com_pose_b=NS(torch=com), joint_stiffness=NS(torch=torch.zeros(8, 12)),
                           joint_damping=NS(torch=torch.zeros(8, 12))))

        def write(field, values, body_ids, env_ids):
            getattr(robot.data, field).torch[env_ids[:, None], body_ids] = values

        robot.set_masses_index = lambda masses, body_ids, env_ids: write("body_mass", masses, body_ids, env_ids)
        robot.set_inertias_index = lambda inertias, body_ids, env_ids: write("body_inertia", inertias, body_ids, env_ids)
        robot.set_coms_index = lambda coms, body_ids, env_ids: write("body_com_pose_b", coms, body_ids, env_ids)

        class Scene(dict):
            num_envs = 8

        events = {}

        def get_term_cfg(name):
            if name not in events:
                raise ValueError(f"No event {name}")
            return events[name]

        env = NS(scene=Scene(robot=robot), device="cpu", num_envs=8,
                 sim=NS(physics_manager=type("PhysxManager", (), {})),
                 event_manager=NS(get_term_cfg=get_term_cfg))
        if randomized:
            cfg.events.add_base_mass.params["asset_cfg"] = cfg.events.base_com.params["asset_cfg"]
            cfg.events.base_com.params["asset_cfg"].body_ids = [0]
            for name, cls in (("add_base_mass", randomize_rigid_body_mass),
                              ("base_com", randomize_rigid_body_com),
                              ("him_actuator_gains", randomize_actuator_gains)):
                term = getattr(cfg.events, name)
                term.func = cls(term, env)
                term.func(env, None, **term.params)
                events[name] = term
            events["physics_material"] = NS(
                func=NS(_impl=NS(num_shapes_per_body=[1] * 5,
                                material_buckets=torch.tensor([[.8, .7, 0.]]))),
                params=cfg.events.physics_material.params)
        return env, robot, events, materials

    def test_actual_defaults_readback_json_and_no_rng_or_state_mutation(self):
        import torch

        env, robot, events, materials = self.fixture()
        before = [robot.data.body_mass.torch.clone(), robot.data.body_inertia.torch.clone(),
                  robot.data.body_com_pose_b.torch.clone(), robot.actuators["base_legs"].stiffness.clone(),
                  robot.actuators["base_legs"].damping.clone(), materials.clone()]
        rng = torch.get_rng_state().clone()
        report = capture_domain_parameters(env)
        json.dumps(report, allow_nan=False)
        torch.testing.assert_close(torch.get_rng_state(), rng, rtol=0, atol=0)
        after = [robot.data.body_mass.torch, robot.data.body_inertia.torch, robot.data.body_com_pose_b.torch,
                 robot.actuators["base_legs"].stiffness, robot.actuators["base_legs"].damping, materials]
        for original, actual in zip(before, after):
            torch.testing.assert_close(original, actual, rtol=0, atol=0)
        ratio = report["base_mass_kg"]["observed_to_default_ratio"]["values"]
        self.assertGreaterEqual(ratio["min"], .8 - 1e-6)
        self.assertLessEqual(ratio["max"], 1.25 + 1e-6)
        self.assertEqual(report["base_mass_kg"]["default"]["values"]["min"], 6.)
        self.assertLess(report["base_inertia_kg_m2"]["mass_scaled_inertia_check"][
            "max_abs_error_from_default_times_mass_ratio_kg_m2"], 1e-7)
        self.assertEqual(report["base_com"]["default_and_offset"]["max_abs_quaternion_change"], 0.)
        pd = report["actuator_pd"]["groups"]["base_legs"]
        self.assertGreaterEqual(pd["stiffness"]["observed"]["min"], 22.5 - 1e-6)
        self.assertLessEqual(pd["stiffness"]["observed"]["max"], 27.5 + 1e-6)
        self.assertEqual(pd["stiffness"]["default"]["values"]["mean"], 25.)
        self.assertEqual(float(robot.data.joint_stiffness.torch.max()), 0.)
        foot = report["foot_material"]
        self.assertEqual(foot["backend_body_ids"], [4, 0, 3, 1])
        self.assertEqual(foot["unique_material_count"], 1)
        self.assertAlmostEqual(foot["static_friction"]["max"], .8)
        self.assertTrue(foot["bucket_pool"]["all_observed_materials_in_bucket_pool"])

    def test_none_and_missing_fields_have_explicit_reasons(self):
        env, robot, _, _ = self.fixture(randomized=False)
        report = capture_domain_parameters(env)
        self.assertEqual(report["base_mass_kg"]["status"], "available")
        self.assertEqual(report["base_mass_kg"]["default"]["status"], "unavailable")
        self.assertIn("reason", report["base_mass_kg"]["default"])
        self.assertEqual(report["base_com"]["default_and_offset"]["status"], "unavailable")
        self.assertEqual(report["foot_material"]["status"], "available")
        self.assertEqual(report["foot_material"]["bucket_pool"]["status"], "unavailable")
        self.assertEqual(report["terrain_material"]["status"], "unavailable")
        self.assertIn("scene.terrain", report["terrain_material"]["reason"])
        pd = report["actuator_pd"]["groups"]["base_legs"]
        self.assertIn("configured reference", pd["stiffness"]["default"]["source"])
        del robot.data.body_com_pose_b
        report = capture_domain_parameters(env)
        self.assertEqual(report["base_com"]["status"], "unavailable")
        self.assertIn("AttributeError", report["base_com"]["reason"])
        self.assertEqual(report["base_mass_kg"]["status"], "available")

    def test_real_gain_event_repeated_resets_remain_relative_to_original_defaults(self):
        env, robot, events, _ = self.fixture()
        for _ in range(20):
            term = events["him_actuator_gains"]
            term.func(env, None, **term.params)
            report = capture_domain_parameters(env)
            pd = report["actuator_pd"]["groups"]["base_legs"]
            for name in ("stiffness", "damping"):
                ratio = pd[name]["default"]["observed_to_default_ratio"]
                self.assertGreaterEqual(ratio["min"], .9 - 1e-6)
                self.assertLessEqual(ratio["max"], 1.1 + 1e-6)


class TerrainMaterialReadbackTest(unittest.TestCase):
    """Real CPU USD stages, physics-purpose resolution and authored attributes."""

    def fixture(self):
        from pxr import Sdf, Usd, UsdGeom, UsdPhysics, UsdShade

        stage = Usd.Stage.CreateInMemory()
        root = UsdGeom.Xform.Define(stage, "/World/ground").GetPrim()
        mesh = UsdGeom.Mesh.Define(stage, "/World/ground/terrain/mesh").GetPrim()
        UsdPhysics.CollisionAPI.Apply(mesh)
        UsdGeom.Mesh.Define(stage, "/World/ground/visual_only")
        material = UsdShade.Material.Define(stage, "/World/ground/terrain/physicsMaterial")
        api = UsdPhysics.MaterialAPI.Apply(material.GetPrim())
        api.CreateStaticFrictionAttr(1.)
        api.CreateDynamicFrictionAttr(.9)
        api.CreateRestitutionAttr(0.)
        # The CPU environment lacks the optional PhysxSchema Python module.
        # Authored token attributes use its verified installed schema names.
        material.GetPrim().CreateAttribute("physxMaterial:frictionCombineMode", Sdf.ValueTypeNames.Token).Set("multiply")
        material.GetPrim().CreateAttribute("physxMaterial:restitutionCombineMode", Sdf.ValueTypeNames.Token).Set("max")
        UsdShade.MaterialBindingAPI.Apply(root).Bind(material, materialPurpose="physics")
        visual = UsdShade.Material.Define(stage, "/World/ground/visualMaterial")
        UsdShade.MaterialBindingAPI.Apply(mesh).Bind(visual)  # Wrong purpose must not win.
        terrain = NS(cfg=NS(prim_path="/World/ground", physics_material=NS(
            static_friction=.2, dynamic_friction=.1, friction_combine_mode="min")),
            terrain_prim_paths=["/World/ground/terrain"])
        return NS(scene=NS(terrain=terrain), sim=NS(stage=stage)), stage, root, mesh, material

    def test_actual_inherited_physics_binding_ignores_visual_and_stale_config_without_mutation(self):
        env, stage, root, mesh, material = self.fixture()
        before = stage.GetRootLayer().ExportToString()
        report = _domain_terrain_material(env)
        self.assertEqual(before, stage.GetRootLayer().ExportToString())
        json.dumps(report, allow_nan=False)
        self.assertEqual(report["terrain_prim_path"], "/World/ground")
        self.assertEqual(report["collision_mesh_count"], 1)
        row = report["collision_meshes"][0]
        self.assertEqual(row["mesh_prim_path"], "/World/ground/terrain/mesh")
        binding = row["physics_binding"]
        self.assertEqual(binding["status"], "available")
        self.assertEqual(binding["material_prim_path"], str(material.GetPath()))
        self.assertEqual(binding["binding_relationship_path"], "/World/ground.material:binding:physics")
        self.assertEqual(binding["attributes"]["static_friction"]["value"], 1.)
        self.assertAlmostEqual(binding["attributes"]["dynamic_friction"]["value"], .9)
        self.assertEqual(binding["attributes"]["friction_combine_mode"]["value"], "multiply")
        self.assertEqual(binding["attributes"]["restitution_combine_mode"]["value"], "max")
        self.assertEqual(binding["attributes"]["damping_combine_mode"]["status"], "unavailable")
        self.assertEqual(report["configured_reference"]["values"]["static_friction"], .2)
        self.assertEqual(report["solver_effective_contact_coefficients"]["status"], "unavailable")

    def test_missing_binding_and_authored_fields_are_independent_unavailable_values(self):
        from pxr import UsdGeom, UsdPhysics, UsdShade

        env, stage, root, mesh, material = self.fixture()
        UsdShade.MaterialBindingAPI(root).UnbindDirectBinding(materialPurpose="physics")
        empty = UsdShade.Material.Define(stage, "/World/ground/emptyMaterial")
        UsdPhysics.MaterialAPI.Apply(empty.GetPrim())  # Schema defaults are not authored measurements.
        UsdShade.MaterialBindingAPI(mesh).Bind(empty, materialPurpose="physics")
        second = UsdGeom.Mesh.Define(stage, "/World/ground/unbound/mesh").GetPrim()
        UsdPhysics.CollisionAPI.Apply(second)
        report = _domain_terrain_material(env)
        self.assertEqual(report["collision_mesh_count"], 2)
        bound = report["collision_meshes"][0]["physics_binding"]
        self.assertEqual(bound["status"], "available")
        for field in bound["attributes"].values():
            self.assertEqual(field["status"], "unavailable")
        unbound = report["collision_meshes"][1]["physics_binding"]
        self.assertEqual(unbound["status"], "unavailable")
        self.assertIn("No resolved physics-purpose", unbound["reason"])

    def test_mesh_override_and_subset_binding_are_resolved_independently(self):
        from pxr import UsdGeom, UsdPhysics, UsdShade

        env, stage, root, mesh, material = self.fixture()
        override = UsdShade.Material.Define(stage, "/World/ground/override")
        UsdPhysics.MaterialAPI.Apply(override.GetPrim()).CreateStaticFrictionAttr(.4)
        UsdShade.MaterialBindingAPI(mesh).Bind(override, materialPurpose="physics")
        subset = UsdGeom.Subset.Define(stage, "/World/ground/terrain/mesh/faceMaterial")
        subset.CreateElementTypeAttr("face")
        subset.CreateIndicesAttr([0])
        UsdShade.MaterialBindingAPI.Apply(subset.GetPrim()).Bind(material, materialPurpose="physics")
        report = _domain_terrain_material(env)
        row = report["collision_meshes"][0]
        self.assertAlmostEqual(row["physics_binding"]["attributes"]["static_friction"]["value"], .4)
        self.assertEqual(row["geometry_subsets"][0]["physics_binding"]["material_prim_path"], str(material.GetPath()))
        self.assertEqual(row["geometry_subsets"][0]["subset_prim_path"], str(subset.GetPath()))

    def test_unavailable_stage_or_mesh_does_not_create_stage_or_use_config_as_measurement(self):
        env, stage, root, mesh, material = self.fixture()
        env.sim.stage = None
        with self.assertRaisesRegex(RuntimeError, "env.sim.stage"):
            _domain_terrain_material(env)
        env.sim.stage = stage
        env.scene.terrain.cfg.prim_path = "/World/missing"
        with self.assertRaisesRegex(ValueError, "absent"):
            _domain_terrain_material(env)


if __name__ == "__main__":
    unittest.main()
