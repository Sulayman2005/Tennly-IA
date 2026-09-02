-- Import de vrais joueurs ATP + WTA + vrais matchs récents (sources : github.com/Tennismylife/TML-Database pour l'ATP, stats.tennismylife.org pour la WTA — voir cahier des charges section 4.2 et le docstring Python pour la note sur la licence ambiguë MIT/non-commerciale).
-- Généré par ml-service/import_real_data.py (v6, ATP + WTA combinés, modele XGBoost si disponible) — NE PAS éditer à la main.
--
-- Limites assumées de cette version (voir en-tête du script Python) :
--   * les matchs sont des résultats RÉCENTS RÉELLEMENT JOUÉS (status='finished'/'walkover'), pas un calendrier de matchs à venir ;
--   * probability_favorite / radar_profile viennent du modèle XGBoost entraîné (train_model.py, combiné ATP+WTA) quand il est disponible, sinon d'un Elo par surface calcule sur plusieurs annees d'historique reel + vraies stats service/retour (repli automatique).

-- DELETE (et non TRUNCATE) : TRUNCATE est bloqué par MySQL des qu'une
-- table est referencee par une cle etrangere, meme table vide, et
-- phpMyAdmin ne garanti pas que SET FOREIGN_KEY_CHECKS=0 reste actif
-- pour toute la suite de l'import. DELETE fonctionne toujours tant que
-- l'ordre enfant -> parent est respecte, ce qui est le cas ici.
DELETE FROM prediction;
DELETE FROM tennis_match;
DELETE FROM player;

INSERT INTO player (id, full_name, country_code, atp_wta_rank, elo_overall, elo_hard, elo_clay, elo_grass, dominant_hand, external_ref, tour) VALUES
  (1, 'Jakub Mensik', 'CZE', 18, 1927, 1957, 1808, 1726, 'R', 'tml:M0NI', 'atp'),
  (2, 'Sebastian Baez', 'ARG', 39, 1814, 1812, 1828, 1759, 'R', 'tml:B0BI', 'atp'),
  (3, 'Tomas Machac', 'CZE', 35, 1880, 1919, 1813, 1748, 'R', 'tml:M0FH', 'atp'),
  (4, 'Ugo Humbert', 'FRA', 36, 1915, 1979, 1701, 1783, 'L', 'tml:HH26', 'atp'),
  (5, 'Ben Shelton', 'USA', 8, 1965, 1960, 1857, 1811, 'L', 'tml:S0S1', 'atp'),
  (6, 'Tommy Paul', 'USA', 21, 1959, 1907, 2004, 1929, 'R', 'tml:PL56', 'atp'),
  (7, 'Alejandro Davidovich Fokina', 'ESP', 15, 1927, 1923, 1866, 1862, 'R', 'tml:DH50', 'atp'),
  (8, 'Jaume Munar', 'ESP', 38, 1849, 1846, 1759, 1818, 'R', 'tml:MU94', 'atp'),
  (9, 'Valentin Vacherot', 'MON', 32, 1844, 1873, 1665, 1638, 'R', 'tml:VA25', 'atp'),
  (10, 'Francisco Cerundolo', 'ARG', 20, 1895, 1900, 1938, 1822, 'R', 'tml:C0AU', 'atp'),
  (11, 'Tallon Griekspoor', 'NED', 25, 1841, 1815, 1840, 1898, 'R', 'tml:GJ37', 'atp'),
  (12, 'Alexander Bublik', 'KAZ', 11, 1997, 1923, 1946, 1956, 'R', 'tml:BK92', 'atp'),
  (13, 'Lorenzo Musetti', 'ITA', 7, 2000, 1948, 2107, 1966, 'R', 'tml:M0EJ', 'atp'),
  (14, 'Daniil Medvedev', 'RUS', 13, 2029, 2054, 2005, 2000, 'R', 'tml:MM58', 'atp'),
  (15, 'Brandon Nakashima', 'USA', 33, 1867, 1863, 1804, 1844, 'R', 'tml:N0AE', 'atp'),
  (16, 'Andrey Rublev', 'RUS', 16, 1905, 1882, 1970, 1972, 'R', 'tml:RE44', 'atp'),
  (17, 'Alex Michelsen', 'USA', 37, 1817, 1830, 1645, 1788, 'R', 'tml:M0QI', 'atp'),
  (18, 'Frances Tiafoe', 'USA', 30, 1849, 1847, 1887, 1892, 'R', 'tml:TD51', 'atp'),
  (19, 'Learner Tien', 'USA', 28, 1898, 1924, 1545, 1636, 'L', 'tml:T0HA', 'atp'),
  (20, 'Coco Gauff', 'USA', 4, 2171, 2199, 2104, 1972, 'R', 'wta:221103', 'wta'),
  (21, 'Ann Li', 'USA', 30, 1825, 1824, 1796, 1706, 'R', 'wta:215983', 'wta'),
  (22, 'Marie Bouzkova', 'CZE', 27, 1924, 1866, 1903, 1917, 'R', 'wta:213631', 'wta'),
  (23, 'Iva Jovic', 'USA', 16, 1887, 1866, 1741, 1684, 'R', 'wta:260300', 'wta'),
  (24, 'Amanda Anisimova', 'USA', 10, 2070, 2083, 1865, 1977, 'R', 'wta:216153', 'wta'),
  (25, 'Alexandra Eala', 'PHI', 20, 1973, 1959, 1706, 1835, 'L', 'wta:223253', 'wta'),
  (26, 'Sorana Cirstea', 'ROU', 19, 1978, 2016, 1874, 1774, 'R', 'wta:201514', 'wta'),
  (27, 'Anna Kalinskaya', 'RUS', 21, 1947, 1936, 1896, 1876, 'R', 'wta:214939', 'wta'),
  (28, 'Jessica Pegula', 'USA', 3, 2148, 2176, 2003, 2044, 'R', 'wta:202468', 'wta'),
  (29, 'Emma Navarro', 'USA', 28, 1900, 1813, 1858, 1916, 'R', 'wta:215613', 'wta'),
  (30, 'Diana Shnaider', 'RUS', 14, 1971, 1960, 1926, 1827, 'L', 'wta:223670', 'wta'),
  (31, 'Maja Chwalinska', 'POL', 21, 1732, 1648, 1782, 1622, 'L', 'wta:216081', 'wta'),
  (32, 'Marta Kostyuk', 'UKR', 11, 2108, 2031, 2069, 1836, 'R', 'wta:216146', 'wta'),
  (33, 'Mirra Andreeva', 'RUS', 6, 2086, 2017, 2114, 1788, 'R', 'wta:259799', 'wta'),
  (34, 'Linda Noskova', 'CZE', 8, 2076, 1994, 1841, 1992, 'R', 'wta:222328', 'wta'),
  (35, 'Elena Rybakina', 'KAZ', 2, 2173, 2242, 2081, 1925, 'R', 'wta:214981', 'wta'),
  (36, 'Iga Swiatek', 'POL', 5, 2178, 2200, 2158, 2134, 'R', 'wta:216347', 'wta');

INSERT INTO tennis_match (id, player_a_id, player_b_id, winner_id, tournament_name, round, surface, scheduled_at, status, score_text) VALUES
  (1, 1, 2, 1, 'Auckland', 'Finale', 'dur', '2026-01-17 12:00:00', 'finished', '6-3 7-6(7)'),
  (2, 3, 4, 3, 'Adelaide', 'Finale', 'dur', '2026-01-17 12:00:00', 'finished', '6-4 6-7(2) 6-2'),
  (3, 2, 5, 2, 'Auckland', 'Quart de finale', 'dur', '2026-01-16 12:00:00', 'finished', '7-5 6-3'),
  (4, 3, 6, 3, 'Adelaide', 'Demi-finale', 'dur', '2026-01-16 12:00:00', 'finished', '2-6 6-3 6-3'),
  (5, 4, 7, 4, 'Adelaide', 'Demi-finale', 'dur', '2026-01-16 12:00:00', 'finished', '6-3 5-7 7-6(4)'),
  (6, 3, 8, 3, 'Adelaide', 'Quart de finale', 'dur', '2026-01-15 12:00:00', 'finished', '6-4 6-4'),
  (7, 7, 9, 7, 'Adelaide', 'Quart de finale', 'dur', '2026-01-15 12:00:00', 'finished', '7-6(4) 6-2'),
  (8, 8, 10, 8, 'Adelaide', '8e de finale', 'dur', '2026-01-14 12:00:00', 'finished', '3-6 7-5 6-4'),
  (9, 4, 11, 4, 'Adelaide', '8e de finale', 'dur', '2026-01-14 12:00:00', 'finished', '6-4 6-1'),
  (10, 12, 13, 12, 'Hong Kong', 'Finale', 'dur', '2026-01-11 12:00:00', 'finished', '7-6(2) 6-3'),
  (11, 14, 15, 14, 'Brisbane', 'Finale', 'dur', '2026-01-11 12:00:00', 'finished', '6-2 7-6(1)'),
  (12, 13, 16, 13, 'Hong Kong', 'Demi-finale', 'dur', '2026-01-10 12:00:00', 'finished', '6-7(3) 7-5 6-4'),
  (13, 14, 17, 14, 'Brisbane', 'Demi-finale', 'dur', '2026-01-10 12:00:00', 'finished', '6-4 6-2'),
  (14, 14, 18, 14, 'Brisbane', '8e de finale', 'dur', '2026-01-07 12:00:00', 'finished', '6-3 6-2'),
  (15, 17, 19, 17, 'Brisbane', '8e de finale', 'dur', '2026-01-07 12:00:00', 'finished', '6-4 6-2'),
  (16, 20, 21, 20, 'Cincinnati', '3e tour', 'dur', '2026-08-13 12:00:00', 'finished', '6-1 7-6(3)'),
  (17, 22, 23, 22, 'Cincinnati', '3e tour', 'dur', '2026-08-13 12:00:00', 'finished', '7-6(0) 7-6(5)'),
  (18, 24, 25, 24, 'Cincinnati', '3e tour', 'dur', '2026-08-13 12:00:00', 'finished', '4-6 6-4 6-2'),
  (19, 26, 27, 26, 'Cincinnati', '3e tour', 'dur', '2026-08-13 12:00:00', 'finished', '6-7(4) 6-1 5-0 RET'),
  (20, 28, 29, 28, 'Cincinnati', '3e tour', 'dur', '2026-08-13 12:00:00', 'finished', '7-5 6-2'),
  (21, 30, 31, 30, 'Cincinnati', '3e tour', 'dur', '2026-08-13 12:00:00', 'finished', '6-2 7-6(3)'),
  (22, 32, 33, 32, 'Cincinnati', '8e de finale', 'dur', '2026-08-13 12:00:00', 'finished', '4-6 6-0 6-2'),
  (23, 28, 26, 28, 'Cincinnati', '8e de finale', 'dur', '2026-08-13 12:00:00', 'finished', '6-2 4-6 7-5'),
  (24, 24, 34, 24, 'Cincinnati', '8e de finale', 'dur', '2026-08-13 12:00:00', 'finished', '6-1 6-4'),
  (25, 35, 30, 35, 'Cincinnati', '8e de finale', 'dur', '2026-08-13 12:00:00', 'finished', '6-4 6-4'),
  (26, 20, 22, 20, 'Cincinnati', '8e de finale', 'dur', '2026-08-13 12:00:00', 'finished', '6-3 6-2'),
  (27, 28, 24, 28, 'Cincinnati', 'Quart de finale', 'dur', '2026-08-13 12:00:00', 'finished', '6-4 2-6 7-6(4)'),
  (28, 36, 35, 36, 'Cincinnati', 'Quart de finale', 'dur', '2026-08-13 12:00:00', 'finished', '4-1 RET'),
  (29, 20, 32, 20, 'Cincinnati', 'Quart de finale', 'dur', '2026-08-13 12:00:00', 'finished', '6-2 6-2'),
  (30, 28, 36, 28, 'Cincinnati', 'Demi-finale', 'dur', '2026-08-13 12:00:00', 'finished', '7-5 4-6 6-4');

INSERT INTO prediction (id, match_id, favorite_player_id, probability_favorite, confidence_level, model_version, computed_at, explanation_factors, radar_profile, market_odds_favorite, value_edge) VALUES
  (1, 1, 1, 0.5409, 'faible', 'xgboost-v1-2026.08', NOW(), '[{"label": "Classement ATP", "favors": "A", "impactPoints": 2.1, "tone": "ok"}, {"label": "Dynamique du moment (Elo sur les derniers matchs)", "favors": "B", "impactPoints": -7.6, "tone": "warn"}, {"label": "Fatigue récente (minutes jouées sur les 10 derniers jours)", "favors": "A", "impactPoints": 2.9, "tone": "ok"}, {"label": "Capacité à créer l\'exploit contre plus fort classé", "favors": "A", "impactPoints": 2.7, "tone": "ok"}]', '{"eloSurface": [56, 40], "forme": [60, 52], "service": [63, 61], "retour": [37, 41], "repos": [10, 10], "h2h": [50, 50]}', NULL, NULL),
  (2, 2, 4, 0.5711, 'moyen', 'xgboost-v1-2026.08', NOW(), '[{"label": "Classement ATP", "favors": "B", "impactPoints": 0.1, "tone": "ok"}, {"label": "Face-à-face", "favors": "B", "impactPoints": 1, "tone": "ok"}, {"label": "Habitude du jeu face à un droitier", "favors": "B", "impactPoints": 2.1, "tone": "ok"}]', '{"eloSurface": [62, 50], "forme": [59, 56], "service": [64, 62], "retour": [37, 39], "repos": [10, 10], "h2h": [60, 40]}', NULL, NULL),
  (3, 3, 5, 0.626, 'moyen', 'xgboost-v1-2026.08', NOW(), '[{"label": "Classement ATP", "favors": "B", "impactPoints": 3.1, "tone": "ok"}, {"label": "Face-à-face", "favors": "B", "impactPoints": 1, "tone": "ok"}, {"label": "Dynamique du moment (Elo sur les derniers matchs)", "favors": "A", "impactPoints": -8.4, "tone": "warn"}, {"label": "Habitude du jeu face à un droitier", "favors": "B", "impactPoints": 1.5, "tone": "ok"}, {"label": "Fatigue récente (minutes jouées sur les 10 derniers jours)", "favors": "B", "impactPoints": 7.5, "tone": "ok"}]', '{"eloSurface": [60, 37], "forme": [60, 52], "service": [66, 61], "retour": [35, 41], "repos": [20, 20], "h2h": [60, 40]}', NULL, NULL),
  (4, 4, 6, 0.5864, 'moyen', 'xgboost-v1-2026.08', NOW(), '[{"label": "Classement ATP", "favors": "B", "impactPoints": 1.4, "tone": "ok"}, {"label": "Face-à-face", "favors": "A", "impactPoints": -1, "tone": "warn"}]', '{"eloSurface": [53, 48], "forme": [65, 56], "service": [63, 62], "retour": [40, 39], "repos": [10, 10], "h2h": [40, 60]}', NULL, NULL),
  (5, 5, 4, 0.5004, 'faible', 'xgboost-v1-2026.08', NOW(), '[{"label": "Classement ATP", "favors": "A", "impactPoints": 2.1, "tone": "ok"}, {"label": "Face-à-face", "favors": "B", "impactPoints": -1, "tone": "warn"}, {"label": "Dynamique du moment (Elo sur les derniers matchs)", "favors": "A", "impactPoints": 3.7, "tone": "ok"}, {"label": "Habitude du jeu face à un droitier", "favors": "B", "impactPoints": -3.1, "tone": "warn"}, {"label": "Fatigue récente (minutes jouées sur les 10 derniers jours)", "favors": "B", "impactPoints": -3.6, "tone": "warn"}]', '{"eloSurface": [61, 55], "forme": [59, 56], "service": [64, 62], "retour": [37, 40], "repos": [10, 10], "h2h": [40, 60]}', NULL, NULL),
  (6, 6, 8, 0.5173, 'faible', 'xgboost-v1-2026.08', NOW(), '[{"label": "Classement ATP", "favors": "B", "impactPoints": 0.3, "tone": "ok"}, {"label": "Dynamique du moment (Elo sur les derniers matchs)", "favors": "B", "impactPoints": 2.0, "tone": "ok"}, {"label": "Fatigue récente (minutes jouées sur les 10 derniers jours)", "favors": "A", "impactPoints": -3.9, "tone": "warn"}]', '{"eloSurface": [45, 46], "forme": [46, 55], "service": [60, 62], "retour": [40, 39], "repos": [10, 10], "h2h": [50, 50]}', NULL, NULL),
  (7, 7, 9, 0.5092, 'faible', 'xgboost-v1-2026.08', NOW(), '[{"label": "Classement ATP", "favors": "B", "impactPoints": 1.7, "tone": "ok"}, {"label": "Face-à-face", "favors": "A", "impactPoints": -1, "tone": "warn"}, {"label": "Dynamique du moment (Elo sur les derniers matchs)", "favors": "B", "impactPoints": 6.0, "tone": "ok"}, {"label": "Fatigue récente (minutes jouées sur les 10 derniers jours)", "favors": "A", "impactPoints": -4.4, "tone": "warn"}, {"label": "Capacité à créer l\'exploit contre plus fort classé", "favors": "B", "impactPoints": 2.4, "tone": "ok"}]', '{"eloSurface": [48, 53], "forme": [63, 55], "service": [63, 62], "retour": [38, 40], "repos": [10, 10], "h2h": [40, 60]}', NULL, NULL),
  (8, 8, 8, 0.5258, 'faible', 'xgboost-v1-2026.08', NOW(), '[{"label": "Classement ATP", "favors": "A", "impactPoints": 1.8, "tone": "ok"}, {"label": "Face-à-face", "favors": "B", "impactPoints": -2, "tone": "warn"}]', '{"eloSurface": [43, 52], "forme": [45, 58], "service": [60, 61], "retour": [40, 40], "repos": [20, 99], "h2h": [30, 70]}', NULL, NULL),
  (9, 9, 4, 0.5986, 'moyen', 'xgboost-v1-2026.08', NOW(), '[{"label": "Classement ATP", "favors": "A", "impactPoints": 1.1, "tone": "ok"}, {"label": "Face-à-face", "favors": "B", "impactPoints": -1, "tone": "warn"}, {"label": "Dynamique du moment (Elo sur les derniers matchs)", "favors": "A", "impactPoints": 3.8, "tone": "ok"}, {"label": "Habitude du jeu face à un droitier", "favors": "B", "impactPoints": -2.0, "tone": "warn"}, {"label": "Fatigue récente (minutes jouées sur les 10 derniers jours)", "favors": "B", "impactPoints": -3.2, "tone": "warn"}]', '{"eloSurface": [58, 41], "forme": [58, 55], "service": [64, 65], "retour": [37, 34], "repos": [20, 70], "h2h": [40, 60]}', NULL, NULL),
  (10, 10, 13, 0.5379, 'faible', 'xgboost-v1-2026.08', NOW(), '[{"label": "Classement ATP", "favors": "B", "impactPoints": 0.4, "tone": "ok"}, {"label": "Face-à-face", "favors": "B", "impactPoints": 0, "tone": "ok"}, {"label": "Fatigue récente (minutes jouées sur les 10 derniers jours)", "favors": "A", "impactPoints": -7.1, "tone": "warn"}]', '{"eloSurface": [58, 51], "forme": [60, 54], "service": [62, 63], "retour": [39, 37], "repos": [10, 10], "h2h": [50, 50]}', NULL, NULL),
  (11, 11, 14, 0.6629, 'eleve', 'xgboost-v1-2026.08', NOW(), '[{"label": "Classement ATP", "favors": "A", "impactPoints": 2.0, "tone": "ok"}, {"label": "Face-à-face", "favors": "A", "impactPoints": 2, "tone": "ok"}, {"label": "Dynamique du moment (Elo sur les derniers matchs)", "favors": "A", "impactPoints": 3.5, "tone": "ok"}]', '{"eloSurface": [68, 46], "forme": [72, 52], "service": [63, 65], "retour": [41, 34], "repos": [10, 10], "h2h": [70, 30]}', NULL, NULL),
  (12, 12, 13, 0.5668, 'moyen', 'xgboost-v1-2026.08', NOW(), '[{"label": "Classement ATP", "favors": "A", "impactPoints": 0.9, "tone": "ok"}, {"label": "Dynamique du moment (Elo sur les derniers matchs)", "favors": "A", "impactPoints": 1.7, "tone": "ok"}, {"label": "Fatigue récente (minutes jouées sur les 10 derniers jours)", "favors": "B", "impactPoints": -2.2, "tone": "warn"}, {"label": "Capacité à créer l\'exploit contre plus fort classé", "favors": "A", "impactPoints": 1.6, "tone": "ok"}]', '{"eloSurface": [57, 49], "forme": [60, 64], "service": [62, 64], "retour": [39, 38], "repos": [10, 10], "h2h": [50, 50]}', NULL, NULL),
  (13, 13, 14, 0.6987, 'eleve', 'xgboost-v1-2026.08', NOW(), '[{"label": "Classement ATP", "favors": "A", "impactPoints": 2.4, "tone": "ok"}, {"label": "Face-à-face", "favors": "A", "impactPoints": 2, "tone": "ok"}]', '{"eloSurface": [67, 43], "forme": [72, 51], "service": [63, 62], "retour": [41, 38], "repos": [10, 10], "h2h": [70, 30]}', NULL, NULL),
  (14, 14, 14, 0.7258, 'eleve', 'xgboost-v1-2026.08', NOW(), '[{"label": "Classement ATP", "favors": "A", "impactPoints": 1.7, "tone": "ok"}, {"label": "Face-à-face", "favors": "A", "impactPoints": 0, "tone": "ok"}, {"label": "Dynamique du moment (Elo sur les derniers matchs)", "favors": "A", "impactPoints": 6.1, "tone": "ok"}]', '{"eloSurface": [66, 45], "forme": [72, 59], "service": [63, 63], "retour": [41, 37], "repos": [20, 30], "h2h": [50, 50]}', NULL, NULL),
  (15, 15, 19, 0.611, 'moyen', 'xgboost-v1-2026.08', NOW(), '[{"label": "Classement ATP", "favors": "B", "impactPoints": 0.9, "tone": "ok"}, {"label": "Face-à-face", "favors": "A", "impactPoints": -1, "tone": "warn"}]', '{"eloSurface": [56, 38], "forme": [60, 51], "service": [61, 62], "retour": [38, 38], "repos": [30, 20], "h2h": [40, 60]}', NULL, NULL),
  (16, 16, 20, 0.8483, 'eleve', 'xgboost-v1-2026.08', NOW(), '[{"label": "Classement WTA", "favors": "A", "impactPoints": 2.6, "tone": "ok"}, {"label": "Face-à-face", "favors": "A", "impactPoints": 1, "tone": "ok"}, {"label": "Dynamique du moment (Elo sur les derniers matchs)", "favors": "A", "impactPoints": 1.6, "tone": "ok"}]', '{"eloSurface": [82, 38], "forme": [75, 50], "service": [58, 57], "retour": [49, 45], "repos": [99, 99], "h2h": [60, 40]}', NULL, NULL),
  (17, 17, 23, 0.5495, 'faible', 'xgboost-v1-2026.08', NOW(), '[{"label": "Classement WTA", "favors": "B", "impactPoints": 1.1, "tone": "ok"}, {"label": "Dynamique du moment (Elo sur les derniers matchs)", "favors": "B", "impactPoints": 3.9, "tone": "ok"}]', '{"eloSurface": [48, 44], "forme": [61, 57], "service": [58, 58], "retour": [48, 47], "repos": [99, 99], "h2h": [50, 50]}', NULL, NULL),
  (18, 18, 24, 0.5857, 'moyen', 'xgboost-v1-2026.08', NOW(), '[{"label": "Classement WTA", "favors": "A", "impactPoints": 1.0, "tone": "ok"}, {"label": "Dynamique du moment (Elo sur les derniers matchs)", "favors": "B", "impactPoints": -6.7, "tone": "warn"}, {"label": "Capacité à créer l\'exploit contre plus fort classé", "favors": "A", "impactPoints": 1.9, "tone": "ok"}]', '{"eloSurface": [72, 59], "forme": [64, 52], "service": [58, 55], "retour": [46, 47], "repos": [99, 99], "h2h": [50, 50]}', NULL, NULL),
  (19, 19, 26, 0.5413, 'faible', 'xgboost-v1-2026.08', NOW(), '[{"label": "Classement WTA", "favors": "A", "impactPoints": 0.2, "tone": "ok"}, {"label": "Face-à-face", "favors": "A", "impactPoints": 1, "tone": "ok"}, {"label": "Dynamique du moment (Elo sur les derniers matchs)", "favors": "B", "impactPoints": -1.6, "tone": "warn"}]', '{"eloSurface": [64, 56], "forme": [57, 59], "service": [58, 57], "retour": [45, 45], "repos": [99, 99], "h2h": [60, 40]}', NULL, NULL),
  (20, 20, 28, 0.7868, 'eleve', 'xgboost-v1-2026.08', NOW(), '[{"label": "Classement WTA", "favors": "A", "impactPoints": 2.5, "tone": "ok"}, {"label": "Face-à-face", "favors": "A", "impactPoints": 3, "tone": "ok"}]', '{"eloSurface": [81, 40], "forme": [74, 60], "service": [59, 57], "retour": [47, 47], "repos": [99, 99], "h2h": [80, 20]}', NULL, NULL),
  (21, 21, 30, 0.7693, 'eleve', 'xgboost-v1-2026.08', NOW(), '[{"label": "Classement WTA", "favors": "A", "impactPoints": 0.7, "tone": "ok"}, {"label": "Face-à-face", "favors": "B", "impactPoints": -1, "tone": "warn"}]', '{"eloSurface": [58, 21], "forme": [60, 53], "service": [58, 55], "retour": [46, 46], "repos": [99, 99], "h2h": [40, 60]}', NULL, NULL),
  (22, 22, 33, 0.5393, 'faible', 'xgboost-v1-2026.08', NOW(), '[{"label": "Classement WTA", "favors": "B", "impactPoints": 0.5, "tone": "ok"}, {"label": "Face-à-face", "favors": "A", "impactPoints": -1, "tone": "warn"}, {"label": "Dynamique du moment (Elo sur les derniers matchs)", "favors": "A", "impactPoints": -1.7, "tone": "warn"}]', '{"eloSurface": [67, 66], "forme": [72, 63], "service": [59, 57], "retour": [48, 46], "repos": [99, 99], "h2h": [40, 60]}', NULL, NULL),
  (23, 23, 28, 0.6769, 'eleve', 'xgboost-v1-2026.08', NOW(), '[{"label": "Classement WTA", "favors": "A", "impactPoints": 1.6, "tone": "ok"}]', '{"eloSurface": [81, 66], "forme": [74, 57], "service": [59, 58], "retour": [47, 45], "repos": [99, 99], "h2h": [50, 50]}', NULL, NULL),
  (24, 24, 24, 0.5244, 'faible', 'xgboost-v1-2026.08', NOW(), '[{"label": "Classement WTA", "favors": "A", "impactPoints": 0.2, "tone": "ok"}, {"label": "Face-à-face", "favors": "A", "impactPoints": 1, "tone": "ok"}, {"label": "Dynamique du moment (Elo sur les derniers matchs)", "favors": "B", "impactPoints": -3.4, "tone": "warn"}]', '{"eloSurface": [73, 63], "forme": [64, 63], "service": [58, 59], "retour": [45, 43], "repos": [99, 99], "h2h": [60, 40]}', NULL, NULL),
  (25, 25, 35, 0.7617, 'eleve', 'xgboost-v1-2026.08', NOW(), '[{"label": "Classement WTA", "favors": "A", "impactPoints": 1.2, "tone": "ok"}, {"label": "Face-à-face", "favors": "A", "impactPoints": 1, "tone": "ok"}, {"label": "Capacité à créer l\'exploit contre plus fort classé", "favors": "A", "impactPoints": 1.7, "tone": "ok"}]', '{"eloSurface": [94, 58], "forme": [76, 60], "service": [61, 58], "retour": [43, 46], "repos": [99, 99], "h2h": [60, 40]}', NULL, NULL),
  (26, 26, 20, 0.7633, 'eleve', 'xgboost-v1-2026.08', NOW(), '[{"label": "Classement WTA", "favors": "A", "impactPoints": 2.3, "tone": "ok"}, {"label": "Face-à-face", "favors": "A", "impactPoints": 0, "tone": "ok"}, {"label": "Dynamique du moment (Elo sur les derniers matchs)", "favors": "A", "impactPoints": 2.7, "tone": "ok"}]', '{"eloSurface": [83, 46], "forme": [75, 57], "service": [58, 58], "retour": [49, 47], "repos": [99, 99], "h2h": [50, 50]}', NULL, NULL),
  (27, 27, 28, 0.5824, 'moyen', 'xgboost-v1-2026.08', NOW(), '[{"label": "Classement WTA", "favors": "A", "impactPoints": 0.7, "tone": "ok"}, {"label": "Face-à-face", "favors": "A", "impactPoints": 4, "tone": "ok"}, {"label": "Dynamique du moment (Elo sur les derniers matchs)", "favors": "B", "impactPoints": -2.5, "tone": "warn"}]', '{"eloSurface": [83, 75], "forme": [74, 64], "service": [59, 58], "retour": [47, 46], "repos": [99, 99], "h2h": [90, 10]}', NULL, NULL),
  (28, 28, 36, 0.5036, 'faible', 'xgboost-v1-2026.08', NOW(), '[{"label": "Classement WTA", "favors": "A", "impactPoints": 0.3, "tone": "ok"}, {"label": "Face-à-face", "favors": "A", "impactPoints": 0, "tone": "ok"}, {"label": "Dynamique du moment (Elo sur les derniers matchs)", "favors": "A", "impactPoints": 2.9, "tone": "ok"}]', '{"eloSurface": [87, 95], "forme": [83, 76], "service": [62, 61], "retour": [50, 43], "repos": [99, 99], "h2h": [50, 50]}', NULL, NULL),
  (29, 29, 20, 0.5829, 'moyen', 'xgboost-v1-2026.08', NOW(), '[{"label": "Classement WTA", "favors": "A", "impactPoints": 0.7, "tone": "ok"}, {"label": "Face-à-face", "favors": "A", "impactPoints": 0, "tone": "ok"}, {"label": "Dynamique du moment (Elo sur les derniers matchs)", "favors": "A", "impactPoints": 1.6, "tone": "ok"}]', '{"eloSurface": [83, 68], "forme": [75, 63], "service": [58, 57], "retour": [49, 46], "repos": [99, 99], "h2h": [50, 50]}', NULL, NULL),
  (30, 30, 36, 0.6102, 'moyen', 'xgboost-v1-2026.08', NOW(), '[{"label": "Classement WTA", "favors": "B", "impactPoints": 0.2, "tone": "ok"}, {"label": "Face-à-face", "favors": "A", "impactPoints": -1, "tone": "warn"}, {"label": "Dynamique du moment (Elo sur les derniers matchs)", "favors": "B", "impactPoints": 3.8, "tone": "ok"}]', '{"eloSurface": [90, 84], "forme": [83, 74], "service": [62, 59], "retour": [50, 47], "repos": [99, 99], "h2h": [40, 60]}', NULL, NULL);
