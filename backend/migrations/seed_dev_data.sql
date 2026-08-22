-- Données de test (dialecte MySQL/MariaDB — voir la note en tête de
-- Version20260101000000.php : adapté depuis la version PostgreSQL d'origine,
-- non rejoué contre un vrai serveur MySQL dans cet environnement).

INSERT INTO plan (code, name, price_cents, currency, billing_period, active) VALUES
  ('classique', 'Classique', 999, 'EUR', 'month', true),
  ('vip', 'VIP', 4999, 'EUR', 'quarter', true),
  ('vip-annuel', 'VIP annuel', 19999, 'EUR', 'year', true);

INSERT INTO player (full_name, country_code, atp_wta_rank, elo_overall, elo_hard, elo_clay, elo_grass, dominant_hand, external_ref) VALUES
  ('Jannik Sinner', 'ITA', 1, 2210, 2245, 2140, 2160, 'R', 'sackmann_sinner_j'),
  ('Carlos Alcaraz', 'ESP', 3, 2180, 2080, 2260, 2150, 'R', 'sackmann_alcaraz_c');

INSERT INTO tennis_match (player_a_id, player_b_id, tournament_name, round, surface, scheduled_at, status) VALUES
  (1, 2, 'US Open', '1er tour', 'dur', '2026-08-19 14:00:00', 'scheduled');

INSERT INTO prediction (match_id, favorite_player_id, probability_favorite, confidence_level, model_version, computed_at, explanation_factors, radar_profile, market_odds_favorite, value_edge) VALUES
  (1, 1, 0.64, 'eleve', 'xgb-2026.08.1', now(),
   '[{"label":"Elo surface","favors":"A","impactPoints":9,"tone":"ok"},{"label":"Face-à-face","favors":"B","impactPoints":-2,"tone":"warn"}]',
   '{"eloSurface":[85,72],"forme":[80,68],"service":[78,73],"retour":[70,74],"repos":[90,60],"h2h":[55,62]}',
   1.55, 0.036);

INSERT INTO app_user (id, email, roles, password, first_name, last_name, created_at) VALUES
  (UUID(), 'sulayman@example.com', '["ROLE_USER"]', '$argon2id$dummy$hash', 'Sulayman', 'Canteau', now());

INSERT INTO subscription (user_id, plan_id, status, current_period_end, created_at)
  SELECT id, (SELECT id FROM plan WHERE code = 'vip'), 'active', NOW() + INTERVAL 3 MONTH, now()
  FROM app_user WHERE email = 'sulayman@example.com';

-- Vérifications
SELECT m.tournament_name, pa.full_name AS joueur_a, pb.full_name AS joueur_b,
       p.probability_favorite, p.confidence_level, fp.full_name AS favori
FROM tennis_match m
JOIN player pa ON pa.id = m.player_a_id
JOIN player pb ON pb.id = m.player_b_id
JOIN prediction p ON p.match_id = m.id
JOIN player fp ON fp.id = p.favorite_player_id;

SELECT u.email, pl.name AS formule, s.status
FROM subscription s
JOIN app_user u ON u.id = s.user_id
JOIN plan pl ON pl.id = s.plan_id;