"""CPU geometry tests, including the void under physical nosing collision slabs."""

import unittest
from copy import deepcopy
from types import SimpleNamespace as NS

import numpy as np
import torch
from isaaclab.terrains import TerrainGenerator

from stair_terrain import (
    StraightStairTerrainCfg, build_stair_generator, configure_stair_batch, configure_stair_terrain,
    heldout_stair_specs, stair_corridor_exit, stair_meshes, stair_metadata,
    stair_goal_reached, stair_terrain_curriculum,
)


def covered_by_box_union(meshes, point):
    """Exact for these axis-aligned closed boxes, avoiding optional rtree extras."""
    point = np.asarray(point)
    return any(np.all(point > mesh.bounds[0] + 1e-9) and np.all(point < mesh.bounds[1] - 1e-9)
               for mesh in meshes)


class StairGeometryTest(unittest.TestCase):
    def test_six_risers_treads_and_landing_coordinates_for_both_directions(self):
        for direction in ("asc", "desc"):
            cfg = StraightStairTerrainCfg(size=(8., 3.), direction=direction, step_height_range=(.16, .16),
                                          step_depth=.27, nosing=0.)
            meshes, origin = stair_meshes(.5, cfg)
            meta = stair_metadata(.16, .27, 0., direction)
            np.testing.assert_allclose(origin, meta["terrain_local_origin"])
            self.assertEqual(len(meta["treads"]), 6)
            self.assertEqual(meta["first_riser_x"], 1.)
            self.assertAlmostEqual(meta["last_riser_x"], 2.35)
            self.assertAlmostEqual(meta["goal_x"], 3.27)
            self.assertEqual(meta["landing_length"], 2.)
            for tread in meta["treads"]:
                x = (tread["x_min"] + tread["x_max"]) / 2 + origin[0]
                top = tread["top_z"] + origin[2]
                self.assertTrue(covered_by_box_union(meshes, (x, origin[1], top - .01)))
                self.assertFalse(covered_by_box_union(meshes, (x, origin[1], top + .01)))
            goal = origin + np.array([meta["goal_x"], 0, meta["goal_platform_z"]])
            self.assertTrue(covered_by_box_union(meshes, goal + [0, 0, -.01]))
            self.assertFalse(covered_by_box_union(meshes, goal + [0, 0, .01]))
            self.assertTrue(all(mesh.is_watertight and mesh.is_winding_consistent for mesh in meshes))

    def test_real_overhang_has_underside_and_empty_space_above_lower_surface(self):
        height, nose, thickness = .17, .03, .02
        for direction in ("asc", "desc"):
            cfg = StraightStairTerrainCfg(size=(8., 3.), direction=direction,
                                          step_height_range=(height, height), step_depth=.25,
                                          nosing=nose, nosing_thickness=thickness)
            meshes, origin = stair_meshes(.0, cfg)
            riser = origin[0] + 1.0
            lip_x = riser - nose / 2 if direction == "asc" else riser + nose / 2
            higher = height if direction == "asc" else 6 * height
            self.assertTrue(covered_by_box_union(meshes, (lip_x, origin[1], higher - thickness / 2)))
            self.assertFalse(covered_by_box_union(meshes, (lip_x, origin[1], higher - thickness - .01)))
            slabs = [mesh for mesh in meshes if mesh.metadata["role"].endswith("nosing")]
            self.assertEqual(len(slabs), 6)
            self.assertTrue(all((mesh.face_normals[:, 2] < -.99).any() for mesh in slabs))
            # The first upward riser retains the complete requested 3 cm lip.
            first = slabs[0]
            self.assertAlmostEqual(first.bounds[1, 0] - first.bounds[0, 0],
                                   (.25 if direction == "asc" else 2.0) + nose)
            self.assertFalse(cfg.convert_to_heightfield)

    def test_generator_integration_moves_mesh_and_spawn_origin_together(self):
        cfg = build_stair_generator(spec={"height": .16, "depth": .27, "direction": "desc", "nosing": .02},
                                    num_rows=1, num_cols=2, seed=3)
        generator = TerrainGenerator(cfg=cfg, device="cpu")
        self.assertEqual(generator.terrain_origins.shape, (1, 2, 3))
        self.assertTrue(np.isfinite(generator.terrain_mesh.vertices).all())
        self.assertTrue(np.isfinite(generator.terrain_origins).all())
        np.testing.assert_allclose(generator.terrain_origins[0, 1] - generator.terrain_origins[0, 0], [0, 3, 0])
        self.assertAlmostEqual(generator.terrain_origins[0, 0, 2], .96)
        self.assertFalse(cfg.sub_terrains["heldout"].convert_to_heightfield)

    def test_hard_stage_contains_full_range_directions_and_every_lip(self):
        cfg = build_stair_generator("hard", num_cols=12)
        variants = list(cfg.sub_terrains.values())
        self.assertEqual(len(variants), 48)
        self.assertGreaterEqual(cfg.num_cols, len(variants))
        self.assertEqual({term.direction for term in variants}, {"asc", "desc"})
        self.assertEqual({term.nosing for term in variants}, {0, .01, .02, .03})
        self.assertEqual({term.step_depth for term in variants}, {.2, .25, .27, .3, .35, .4})
        self.assertTrue(all(term.step_height_range == (.08, .23) for term in variants))
        self.assertTrue(all(not term.convert_to_heightfield for term in variants))
        for spec in heldout_stair_specs():
            selected = build_stair_generator("easy", spec=spec, num_rows=1, num_cols=1)
            meshes, _ = stair_meshes(.5, selected.sub_terrains["heldout"].replace(size=selected.size))
            self.assertGreater(len(meshes), 1)

    def test_bootstrap_stairs_remain_closed_and_above_nosing_thickness(self):
        cfg = build_stair_generator("bootstrap", num_rows=3, num_cols=4, seed=17)
        variants = list(cfg.sub_terrains.values())
        self.assertEqual(len(variants), 4)
        self.assertEqual({term.direction for term in variants}, {"asc", "desc"})
        self.assertEqual({term.step_depth for term in variants}, {.30, .36})
        self.assertTrue(all(term.step_height_range == (.025, .08) and term.nosing == 0.
                            for term in variants))
        for term in variants:
            for difficulty in np.linspace(0., 1., 11):
                meshes, origin = stair_meshes(difficulty, term.replace(size=cfg.size))
                geometry = meshes[0].metadata["stair_geometry"]
                self.assertGreater(geometry["step_height"], term.nosing_thickness)
                self.assertEqual(len(geometry["treads"]), 6)
                self.assertTrue(np.isfinite(origin).all())
                self.assertTrue(all(mesh.is_watertight and mesh.is_winding_consistent and
                                    np.isfinite(mesh.vertices).all() and mesh.volume > 0
                                    for mesh in meshes))
        generated = TerrainGenerator(cfg, device="cpu")
        self.assertEqual(generated.terrain_origins.shape, (3, 4, 3))
        self.assertTrue(np.isfinite(generated.terrain_origins).all())
        self.assertTrue(np.isfinite(generated.terrain_mesh.vertices).all())

    def test_invalid_geometry_does_not_create_mesh(self):
        for params in ({"step_height": 0}, {"step_depth": .01, "nosing": .02},
                       {"direction": "sideways"}, {"size": (3., 3.)}, {"nosing": -.01},
                       {"step_height": float("nan")}):
            with self.assertRaises(ValueError):
                stair_metadata(**params)

    def test_directed_curriculum_does_not_reward_backwards_distance_or_fall(self):
        generator = build_stair_generator("easy", num_rows=2, num_cols=8)
        terrain = NS(cfg=NS(terrain_generator=generator), terrain_types=torch.tensor([0, 0, 0, 0]),
                     terrain_levels=torch.zeros(4, dtype=torch.long))
        recorded = []
        terrain.update_env_origins = lambda ids, up, down: recorded.append((ids.clone(), up.clone(), down.clone()))
        data = NS(root_pos_w=NS(torch=torch.tensor([[5., 0., 0.], [-5., 0., 0.], [5., 0., 0.], [.1, .8, 0.]])))
        env = NS(device="cpu", scene={"robot": NS(data=data)},
                 termination_manager=NS(terminated=torch.tensor([False, False, True, True])))
        # Add scene attributes required by the real manager term.
        class Scene(dict):
            pass
        env.scene = Scene(env.scene)
        env.scene.terrain, env.scene.env_origins = terrain, torch.zeros(4, 3)
        stair_terrain_curriculum(env, [0, 1, 2, 3])
        torch.testing.assert_close(recorded[0][1], torch.tensor([True, False, False, False]))
        torch.testing.assert_close(recorded[0][2], torch.tensor([False, True, True, True]))
        torch.testing.assert_close(stair_corridor_exit(env), torch.tensor([False, False, False, True]))

    def test_curriculum_reports_direction_failures_without_hiding_ascent(self):
        generator = build_stair_generator("easy", num_rows=10, num_cols=8)
        terrain = NS(cfg=NS(terrain_generator=generator), terrain_types=torch.tensor([0, 0, 4, 4]),
                     terrain_levels=torch.tensor([2, 4, 6, 8]))
        recorded = []
        terrain.update_env_origins = lambda ids, up, down: recorded.append((ids.clone(), up.clone(), down.clone()))
        data = NS(root_pos_w=NS(torch=torch.tensor([[.2, 0., 0.], [5., 0., 0.],
                                                  [5., 0., 0.], [5., 0., 0.]])))
        true_goals = torch.tensor([False, True, True, True])
        manager = NS(terminated=torch.tensor([True, True, False, False]), get_term=lambda _: true_goals)
        class Scene(dict):
            pass
        scene = Scene(robot=NS(data=data))
        scene.terrain, scene.env_origins = terrain, torch.zeros(4, 3)
        env = NS(device="cpu", scene=scene, termination_manager=manager)
        diagnostics = stair_terrain_curriculum(env, [0, 1, 2, 3])
        self.assertEqual(float(diagnostics["levels_mean"]), 5.)
        self.assertEqual(float(diagnostics["asc_levels_mean"]), 3.)
        self.assertEqual(float(diagnostics["desc_levels_mean"]), 7.)
        self.assertEqual(float(diagnostics["asc_goal_fraction"]), 0.)
        self.assertEqual(float(diagnostics["desc_goal_fraction"]), 1.)
        self.assertEqual(float(diagnostics["asc_terminated_fraction"]), 1.)
        self.assertEqual(float(diagnostics["desc_terminated_fraction"]), 0.)
        self.assertEqual(int(diagnostics["asc_reset_count"]), 2)
        self.assertEqual(int(diagnostics["desc_reset_count"]), 2)
        torch.testing.assert_close(recorded[0][1], torch.tensor([False, False, True, True]))
        # The subset contains ascent failures only: descent fractions must be
        # zero with count=0, rather than NaN or fictitious new success samples.
        diagnostics = stair_terrain_curriculum(env, [0, 1])
        self.assertEqual(float(diagnostics["desc_goal_fraction"]), 0.)
        self.assertEqual(float(diagnostics["desc_terminated_fraction"]), 0.)
        self.assertEqual(int(diagnostics["desc_reset_count"]), 0)
        self.assertTrue(all(bool(torch.isfinite(value)) for value in diagnostics.values()))

    def test_curriculum_goal_diagnostics_use_real_goal_term_not_progress_alone(self):
        generator = build_stair_generator("easy", num_rows=2, num_cols=8)
        terrain = NS(cfg=NS(terrain_generator=generator), terrain_types=torch.tensor([0, 0]),
                     terrain_levels=torch.zeros(2, dtype=torch.long))
        terrain.update_env_origins = lambda ids, up, down: None
        class Scene(dict):
            pass
        scene = Scene(robot=NS(data=NS(root_pos_w=NS(torch=torch.tensor([[5., 0., 0.], [5., 0., 0.]])))))
        scene.terrain, scene.env_origins = terrain, torch.zeros(2, 3)
        manager = NS(terminated=torch.zeros(2, dtype=torch.bool),
                     get_term=lambda _: torch.tensor([False, True]))
        env = NS(device="cpu", scene=scene, termination_manager=manager)
        diagnostics = stair_terrain_curriculum(env, [0, 1])
        self.assertEqual(float(diagnostics["asc_goal_fraction"]), .5)
        self.assertEqual(float(diagnostics["asc_terminated_fraction"]), 0.)
        self.assertEqual(float(diagnostics["desc_levels_mean"]), 0.)
        diagnostics = stair_terrain_curriculum(env, [])
        self.assertEqual(int(diagnostics["asc_reset_count"]), 0)
        self.assertEqual(float(diagnostics["asc_goal_fraction"]), 0.)
        self.assertTrue(all(bool(torch.isfinite(value)) for value in diagnostics.values()))

    def test_curriculum_does_not_promote_root_beyond_goal_without_actual_goal(self):
        generator = build_stair_generator("easy", num_rows=2, num_cols=8)
        terrain = NS(cfg=NS(terrain_generator=generator), terrain_types=torch.tensor([0, 0, 0]),
                     terrain_levels=torch.zeros(3, dtype=torch.long))
        recorded = []
        terrain.update_env_origins = lambda ids, up, down: recorded.append((ids.clone(), up.clone(), down.clone()))
        class Scene(dict):
            pass
        scene = Scene(robot=NS(data=NS(root_pos_w=NS(torch=torch.tensor([[5., 0., .3]]).repeat(3, 1)))))
        scene.terrain, scene.env_origins = terrain, torch.zeros(3, 3)
        manager = NS(terminated=torch.tensor([False, False, True]),
                     get_term=lambda _: torch.tensor([False, True, True]))
        env = NS(device="cpu", scene=scene, termination_manager=manager)
        stair_terrain_curriculum(env, [0, 1, 2])
        torch.testing.assert_close(recorded[0][1], torch.tensor([False, True, False]))
        torch.testing.assert_close(recorded[0][2], torch.tensor([False, False, True]))

    def test_training_goal_requires_feet_upright_height_and_corridor(self):
        generator = build_stair_generator("easy", num_rows=2, num_cols=8)
        n = 7
        terrain = NS(cfg=NS(terrain_generator=generator), terrain_types=torch.zeros(n, dtype=torch.long))
        roots = torch.tensor([[3.5, 0., .3]]).repeat(n, 1)
        roots[1, 0], roots[2, 1], roots[3, 2] = 2., .7, .1
        gravity = torch.tensor([[0., 0., -1.]]).repeat(n, 1)
        gravity[4, 2] = -.7
        feet = torch.tensor([[[3.1, 0., 0.]]]).repeat(n, 4, 1)
        feet[5, 0, 0] = 1.5
        hits = torch.zeros(n, 63, 3)
        hits[6, 0, 2] = float("inf")
        calls = []
        robot = NS(data=NS(root_pos_w=NS(torch=roots), projected_gravity_b=NS(torch=gravity),
                           body_pos_w=NS(torch=feet)))
        robot.find_bodies = lambda name: (calls.append(name) or ([0, 1, 2, 3], ["foot"] * 4))
        class Scene(dict):
            pass
        scene = Scene(robot=robot, base_height_scanner=NS(data=NS(ray_hits_w=NS(torch=hits))))
        scene.terrain, scene.env_origins = terrain, torch.zeros(n, 3)
        env = NS(device="cpu", scene=scene)
        expected = torch.tensor([True, False, False, False, False, False, False])
        torch.testing.assert_close(stair_goal_reached(env), expected)
        cached = env._him_stair_column_geometry
        torch.testing.assert_close(stair_goal_reached(env), expected)
        self.assertIs(cached, env._him_stair_column_geometry)
        self.assertEqual(len(calls), 1)

    def test_goal_timeout_is_only_enabled_for_training(self):
        class Scanner(NS):
            def copy(self):
                return deepcopy(self)
        cfg = NS(scene=NS(height_scanner=Scanner(), terrain=NS()), sim=NS(dt=.005),
                 decimation=4, terminations=NS(), curriculum=NS())
        manifest = configure_stair_terrain(cfg)
        self.assertFalse(manifest["heldout"])
        self.assertTrue(cfg.terminations.stair_goal_reached.time_out)
        self.assertEqual(cfg.scene.base_height_scanner.update_period, .02)
        manifest = configure_stair_terrain(cfg, spec={"height": .17, "depth": .25, "nosing": .03})
        self.assertTrue(manifest["heldout"])
        self.assertIsNone(cfg.terminations.stair_goal_reached)
        self.assertIsNone(cfg.curriculum.terrain_levels)

    def test_batch_specs_have_deterministic_columns_and_fixed_heights(self):
        class Scanner(NS):
            def copy(self):
                return deepcopy(self)
        cfg = NS(scene=NS(height_scanner=Scanner(), terrain=NS(), num_envs=128), sim=NS(dt=.005),
                 decimation=4, terminations=NS(), curriculum=NS())
        specs = [{"name": f"{direction}_{height}", "direction": direction, "height": height, "depth": .27}
                 for direction in ("asc", "desc") for height in (.08, .16)]
        manifest = configure_stair_batch(cfg, specs, seed=11)
        generator_cfg = cfg.scene.terrain.terrain_generator
        self.assertEqual((generator_cfg.num_rows, generator_cfg.num_cols), (1, 4))
        self.assertTrue(generator_cfg.curriculum)
        self.assertIsNone(cfg.curriculum.terrain_levels)
        self.assertIsNone(cfg.terminations.stair_goal_reached)
        self.assertEqual(cfg.scene.terrain.max_init_terrain_level, 0)
        self.assertEqual(manifest["variant_names"], [spec["name"] for spec in specs])
        self.assertEqual(len(manifest["geometry"]), len(specs))
        variants = list(generator_cfg.sub_terrains.values())
        for variant, column in zip(variants, manifest["columns"]):
            low_mesh, low_origin = stair_meshes(0., variant.replace(size=generator_cfg.size))
            high_mesh, high_origin = stair_meshes(1., variant.replace(size=generator_cfg.size))
            np.testing.assert_allclose(low_origin, high_origin)
            np.testing.assert_allclose(low_mesh[-1].vertices, high_mesh[-1].vertices)
            self.assertEqual(column["geometry"]["direction"], variant.direction)
            self.assertEqual(column["geometry"]["step_height"], variant.step_height_range[0])
        generated = TerrainGenerator(cfg=generator_cfg, device="cpu")
        expected_z = [0., 0., .48, .96]
        np.testing.assert_allclose(generated.terrain_origins[0, :, 2], expected_z)
        # Distinct tile origins retain the expected fixed geometries despite
        # randomly drawn per-row difficulty in the curriculum generator.
        self.assertEqual(generated.terrain_origins.shape, (1, 4, 3))
        self.assertEqual(manifest["environment_column_mapping"], "scene.terrain.terrain_types")

    def test_empty_batch_rejected_before_configuration(self):
        cfg = NS()
        with self.assertRaisesRegex(ValueError, "at least one"):
            configure_stair_batch(cfg, [])

    def test_fixed_long_flights_expand_tiles_and_preserve_every_riser(self):
        for direction in ("asc", "desc"):
            for count, depth, expected_size in ((10, .25, 8.), (12, .25, 8.), (12, .40, 10.)):
                selected = build_stair_generator(spec={"height": .17, "depth": depth,
                                                       "direction": direction, "num_steps": count})
                self.assertEqual(selected.size, (expected_size, 3.))
                term = selected.sub_terrains["heldout"].replace(size=selected.size)
                meshes, origin = stair_meshes(.5, term)
                geometry = meshes[0].metadata["stair_geometry"]
                self.assertEqual(len(geometry["treads"]), count)
                self.assertAlmostEqual(abs(geometry["goal_platform_z"]), count * .17)
                for tread in geometry["treads"]:
                    position = origin + [(tread["x_min"] + tread["x_max"]) / 2., 0., tread["top_z"]]
                    self.assertTrue(covered_by_box_union(meshes, position + [0., 0., -.01]))
                    self.assertFalse(covered_by_box_union(meshes, position + [0., 0., .01]))
                self.assertTrue(all((mesh.bounds[:, 0] >= 0.).all() and
                                    (mesh.bounds[:, 0] <= expected_size + 1e-9).all() for mesh in meshes))
        for count in (.5, 6.5, float("inf"), float("nan")):
            with self.assertRaises(ValueError):
                build_stair_generator(spec={"num_steps": count})

    def test_mixed_length_batch_uses_one_common_size_and_per_column_widths(self):
        class Scanner(NS):
            def copy(self):
                return deepcopy(self)
        cfg = NS(scene=NS(height_scanner=Scanner(), terrain=NS()), sim=NS(dt=.005),
                 decimation=4, terminations=NS(), curriculum=NS())
        specs = [{"name": "short", "height": .16, "depth": .27},
                 {"name": "long_desc", "height": .17, "depth": .4,
                  "num_steps": 12, "direction": "desc", "width": 1.6}]
        manifest = configure_stair_batch(cfg, specs)
        generator_cfg = cfg.scene.terrain.terrain_generator
        self.assertEqual(generator_cfg.size, (10., 3.))
        self.assertEqual(manifest["terrain_size"], [10., 3.])
        self.assertIsNone(manifest["num_steps"])
        self.assertIsNone(manifest["width"])
        for term, column in zip(generator_cfg.sub_terrains.values(), manifest["columns"]):
            meshes, origin = stair_meshes(.4, term.replace(size=generator_cfg.size))
            self.assertEqual(column["geometry"]["terrain_size"], [10., 3.])
            np.testing.assert_allclose(origin, column["geometry"]["terrain_local_origin"])
            self.assertEqual(meshes[0].bounds[1, 0], 10.)
        generated = TerrainGenerator(generator_cfg, device="cpu")
        np.testing.assert_allclose(generated.terrain_origins[0, :, 2], [0., 2.04])
        terrain = NS(cfg=NS(terrain_generator=generator_cfg), terrain_types=torch.tensor([0, 1]))
        class Scene(dict):
            pass
        scene = Scene(robot=NS(data=NS(root_pos_w=NS(torch=torch.tensor([[0., .7, 0.], [0., .7, 0.]])))))
        scene.terrain, scene.env_origins = terrain, torch.zeros(2, 3)
        env = NS(device="cpu", scene=scene)
        torch.testing.assert_close(stair_corridor_exit(env), torch.tensor([True, False]))


if __name__ == "__main__":
    unittest.main()
