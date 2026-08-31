-- Journal de l'exécution du 2026-08-31 19:56:07
-- (déjà appliqué directement en base — ce fichier est juste une trace lisible, ne pas le réimporter.)

-- Joueurs existants dont l'Elo (et/ou le circuit, voir resolve_player) a été rafraîchi :
UPDATE player SET elo_overall=1710, elo_hard=1697, elo_clay=1629, elo_grass=1654, atp_wta_rank=97, tour='wta' WHERE id=188;
UPDATE player SET elo_overall=2101, elo_hard=2131, elo_clay=1921, elo_grass=1832, atp_wta_rank=7, tour='wta' WHERE id=212;

-- Nouveaux matchs à venir (ATP + WTA) :
INSERT INTO tennis_match (id, player_a_id, player_b_id, winner_id, tournament_name, round, surface, scheduled_at, status, score_text, external_ref) VALUES (181, 174, 188, NULL, 'US Open', '2e tour', 'dur', '2026-09-02 15:00:00', 'scheduled', NULL, 'livetennisapi:184695');
INSERT INTO tennis_match (id, player_a_id, player_b_id, winner_id, tournament_name, round, surface, scheduled_at, status, score_text, external_ref) VALUES (182, 212, 205, NULL, 'US Open', '2e tour', 'dur', '2026-09-02 15:00:00', 'scheduled', NULL, 'livetennisapi:184696');

-- Nouvelles analyses :
INSERT INTO prediction (id, match_id, favorite_player_id, probability_favorite, confidence_level, model_version, computed_at, explanation_factors, radar_profile, market_odds_favorite, value_edge) VALUES (181, 181, 174, 0.6684, 'eleve', 'xgboost-v1-2026.08', NOW(), '[{"label": "Classement WTA", "favors": "A", "impactPoints": 6.5, "tone": "ok"}]', '{"eloSurface": [46, 25], "forme": [65, 55], "service": [60, 55], "retour": [60, 48], "repos": [30, 99], "h2h": [50, 50]}', NULL, NULL);
INSERT INTO prediction (id, match_id, favorite_player_id, probability_favorite, confidence_level, model_version, computed_at, explanation_factors, radar_profile, market_odds_favorite, value_edge) VALUES (182, 182, 212, 0.8286, 'eleve', 'xgboost-v1-2026.08', NOW(), '[{"label": "Classement WTA", "favors": "A", "impactPoints": 5.3, "tone": "ok"}]', '{"eloSurface": [79, 36], "forme": [70, 65], "service": [60, 60], "retour": [44, 60], "repos": [99, 30], "h2h": [50, 50]}', NULL, NULL);
