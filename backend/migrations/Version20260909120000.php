<?php

declare(strict_types=1);

namespace DoctrineMigrations;

use Doctrine\DBAL\Schema\Schema;
use Doctrine\Migrations\AbstractMigration;

/**
 * Crée player_career_stats : palmarès carrière complet par joueur (LiveTennisAPI,
 * palier Basic, endpoint /history/archive/career) — victoires/défaites par
 * surface, statistiques de service, période couverte. Table brute (pas
 * d'entité Doctrine), même convention que player_snapshot / player_head_to_head
 * (voir Version20260908150000) : alimentée par
 * ml-service/import_career_stats_livetennisapi.py, lue via Doctrine DBAL
 * Connection (pas de repository), jamais par l'ORM.
 *
 * Toutes les colonnes de stats sont nullables : certains joueurs ont un
 * historique de service incomplet côté LiveTennisAPI (matches_with_stats
 * plus faible que le nombre réel de matchs), voire aucune donnée sur
 * certaines surfaces (carpet, quasiment disparu du circuit depuis 2010).
 */
final class Version20260909120000 extends AbstractMigration
{
    public function getDescription(): string
    {
        return 'Crée player_career_stats (palmarès carrière LiveTennisAPI : surface, service, période).';
    }

    public function up(Schema $schema): void
    {
        $this->addSql(<<<'SQL'
            CREATE TABLE player_career_stats (
                player_id INT NOT NULL,
                wins INT DEFAULT NULL,
                losses INT DEFAULT NULL,
                titles INT DEFAULT NULL,
                wins_hard INT DEFAULT NULL,
                losses_hard INT DEFAULT NULL,
                wins_clay INT DEFAULT NULL,
                losses_clay INT DEFAULT NULL,
                wins_grass INT DEFAULT NULL,
                losses_grass INT DEFAULT NULL,
                wins_carpet INT DEFAULT NULL,
                losses_carpet INT DEFAULT NULL,
                aces INT DEFAULT NULL,
                aces_per_match DOUBLE DEFAULT NULL,
                double_faults INT DEFAULT NULL,
                first_in_pct DOUBLE DEFAULT NULL,
                first_won_pct DOUBLE DEFAULT NULL,
                second_won_pct DOUBLE DEFAULT NULL,
                bp_saved_pct DOUBLE DEFAULT NULL,
                span_first DATE DEFAULT NULL,
                span_last DATE DEFAULT NULL,
                updated_at DATETIME NOT NULL,
                PRIMARY KEY(player_id),
                CONSTRAINT fk_career_stats_player FOREIGN KEY (player_id) REFERENCES player (id) ON DELETE CASCADE
            ) DEFAULT CHARACTER SET utf8mb4
        SQL);
    }

    public function down(Schema $schema): void
    {
        $this->addSql('DROP TABLE player_career_stats');
    }
}
