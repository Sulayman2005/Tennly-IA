-- Journal de l'exécution du 2026-08-28 19:34:20
-- (déjà appliqué directement en base — ce fichier est juste une trace lisible, ne pas le réimporter.)

-- Joueurs existants dont l'Elo (et/ou le circuit, voir resolve_player) a été rafraîchi :
UPDATE player SET elo_overall=1662, elo_hard=1576, elo_clay=1687, elo_grass=1576, atp_wta_rank=36, tour='atp' WHERE id=63;
UPDATE player SET elo_overall=1798, elo_hard=1816, elo_clay=1779, elo_grass=1744, atp_wta_rank=109, tour='atp' WHERE id=60;
UPDATE player SET elo_overall=1698, elo_hard=1690, elo_clay=1711, elo_grass=1723, atp_wta_rank=79, tour='atp' WHERE id=67;
UPDATE player SET elo_overall=1634, elo_hard=1633, elo_clay=1629, elo_grass=1622, atp_wta_rank=37, tour='atp' WHERE id=66;
UPDATE player SET elo_overall=1806, elo_hard=1801, elo_clay=1796, elo_grass=1706, atp_wta_rank=30, tour='wta' WHERE id=143;
UPDATE player SET elo_overall=1822, elo_hard=1789, elo_clay=1794, elo_grass=1781, atp_wta_rank=50, tour='wta' WHERE id=146;
UPDATE player SET elo_overall=1930, elo_hard=1868, elo_clay=1894, elo_grass=1922, atp_wta_rank=24, tour='wta' WHERE id=149;

-- Nouveaux matchs à venir (ATP + WTA) :
INSERT INTO tennis_match (id, player_a_id, player_b_id, winner_id, tournament_name, round, surface, scheduled_at, status, score_text, external_ref) VALUES (154, 63, 60, NULL, 'Winston-Salem', 'Demi-finale', 'dur', '2026-08-28 20:00:00', 'scheduled', NULL, 'livetennisapi:180049');
INSERT INTO tennis_match (id, player_a_id, player_b_id, winner_id, tournament_name, round, surface, scheduled_at, status, score_text, external_ref) VALUES (155, 67, 66, NULL, 'Winston-Salem', 'Demi-finale', 'dur', '2026-08-28 22:30:00', 'scheduled', NULL, 'livetennisapi:180078');
INSERT INTO tennis_match (id, player_a_id, player_b_id, winner_id, tournament_name, round, surface, scheduled_at, status, score_text, external_ref) VALUES (156, 143, 146, NULL, 'Monterrey', 'Demi-finale', 'dur', '2026-08-28 23:00:00', 'scheduled', NULL, 'livetennisapi:180075');
INSERT INTO tennis_match (id, player_a_id, player_b_id, winner_id, tournament_name, round, surface, scheduled_at, status, score_text, external_ref) VALUES (157, 145, 149, NULL, 'Monterrey', 'Demi-finale', 'dur', '2026-08-29 01:00:00', 'scheduled', NULL, 'livetennisapi:180080');

-- Nouvelles analyses :
INSERT INTO prediction (id, match_id, favorite_player_id, probability_favorite, confidence_level, model_version, computed_at, explanation_factors, radar_profile, market_odds_favorite, value_edge) VALUES (154, 154, 60, 0.6592, 'eleve', 'xgboost-v1-2026.08', NOW(), '[{"label": "Classement ATP", "favors": "B", "impactPoints": 7.3, "tone": "ok"}, {"label": "Dynamique du moment (Elo sur les derniers matchs)", "favors": "A", "impactPoints": -4.0, "tone": "warn"}]', '{"eloSurface": [9, 39], "forme": [57, 45], "service": [61, 63], "retour": [36, 36], "repos": [99, 99], "h2h": [50, 50]}', NULL, NULL);
INSERT INTO prediction (id, match_id, favorite_player_id, probability_favorite, confidence_level, model_version, computed_at, explanation_factors, radar_profile, market_odds_favorite, value_edge) VALUES (155, 155, 67, 0.6027, 'moyen', 'xgboost-v1-2026.08', NOW(), '[{"label": "Classement ATP", "favors": "A", "impactPoints": 4.2, "tone": "ok"}]', '{"eloSurface": [24, 17], "forme": [36, 33], "service": [63, 61], "retour": [32, 35], "repos": [99, 99], "h2h": [50, 50]}', NULL, NULL);
INSERT INTO prediction (id, match_id, favorite_player_id, probability_favorite, confidence_level, model_version, computed_at, explanation_factors, radar_profile, market_odds_favorite, value_edge) VALUES (156, 156, 143, 0.5118, 'faible', 'xgboost-v1-2026.08', NOW(), '[{"label": "Classement WTA", "favors": "A", "impactPoints": 2.0, "tone": "ok"}, {"label": "Face-à-face", "favors": "B", "impactPoints": -1, "tone": "warn"}]', '{"eloSurface": [38, 36], "forme": [50, 51], "service": [57, 57], "retour": [45, 40], "repos": [99, 99], "h2h": [40, 60]}', NULL, NULL);
INSERT INTO prediction (id, match_id, favorite_player_id, probability_favorite, confidence_level, model_version, computed_at, explanation_factors, radar_profile, market_odds_favorite, value_edge) VALUES (157, 157, 149, 0.5833, 'moyen', 'xgboost-v1-2026.08', NOW(), '[{"label": "Classement WTA", "favors": "B", "impactPoints": 1.4, "tone": "ok"}]', '{"eloSurface": [44, 46], "forme": [65, 58], "service": [60, 58], "retour": [60, 46], "repos": [30, 99], "h2h": [50, 50]}', NULL, NULL);
