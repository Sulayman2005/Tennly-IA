<?php

declare(strict_types=1);

namespace DoctrineMigrations;

use Doctrine\DBAL\Schema\Schema;
use Doctrine\Migrations\AbstractMigration;

/**
 * Auto-generated Migration: Please modify to your needs!
 */
final class Version20260908132625 extends AbstractMigration
{
    public function getDescription(): string
    {
        return '';
    }

    public function up(Schema $schema): void
    {
        // this up() migration is auto-generated, please modify it to your needs
        $this->addSql('ALTER TABLE app_user CHANGE id id CHAR(36) NOT NULL COMMENT \'(DC2Type:guid)\', CHANGE created_at created_at DATETIME NOT NULL COMMENT \'(DC2Type:datetime_immutable)\'');
        $this->addSql('ALTER TABLE plan RENAME INDEX uniq_plan_code TO UNIQ_DD5A5B7D77153098');
        $this->addSql('ALTER TABLE player ADD tour VARCHAR(3) NOT NULL, CHANGE birth_date birth_date DATETIME DEFAULT NULL COMMENT \'(DC2Type:datetime_immutable)\'');
        $this->addSql('ALTER TABLE player RENAME INDEX uniq_player_external_ref TO UNIQ_98197A65B445906B');
        $this->addSql('ALTER TABLE prediction CHANGE computed_at computed_at DATETIME NOT NULL COMMENT \'(DC2Type:datetime_immutable)\'');
        $this->addSql('ALTER TABLE prediction RENAME INDEX uniq_prediction_match TO UNIQ_36396FC82ABEACD6');
        $this->addSql('ALTER TABLE prediction RENAME INDEX fk_prediction_favorite TO IDX_36396FC853F6604D');
        $this->addSql('ALTER TABLE refresh_token RENAME INDEX uniq_refresh_token TO UNIQ_C74F2195C74F2195');
        $this->addSql('ALTER TABLE subscription CHANGE user_id user_id CHAR(36) NOT NULL COMMENT \'(DC2Type:guid)\', CHANGE current_period_end current_period_end DATETIME DEFAULT NULL COMMENT \'(DC2Type:datetime_immutable)\', CHANGE created_at created_at DATETIME NOT NULL COMMENT \'(DC2Type:datetime_immutable)\', CHANGE canceled_at canceled_at DATETIME DEFAULT NULL COMMENT \'(DC2Type:datetime_immutable)\'');
        $this->addSql('ALTER TABLE subscription RENAME INDEX idx_subscription_user TO IDX_A3C664D3A76ED395');
        $this->addSql('ALTER TABLE subscription RENAME INDEX fk_subscription_plan TO IDX_A3C664D3E899029B');
        $this->addSql('DROP INDEX idx_match_scheduled_at ON tennis_match');
        $this->addSql('ALTER TABLE tennis_match ADD external_ref VARCHAR(60) DEFAULT NULL, CHANGE scheduled_at scheduled_at DATETIME NOT NULL COMMENT \'(DC2Type:datetime_immutable)\'');
        $this->addSql('CREATE UNIQUE INDEX UNIQ_7510D177B445906B ON tennis_match (external_ref)');
        $this->addSql('ALTER TABLE tennis_match RENAME INDEX idx_match_player_a TO IDX_7510D17799C4036B');
        $this->addSql('ALTER TABLE tennis_match RENAME INDEX idx_match_player_b TO IDX_7510D1778B71AC85');
        $this->addSql('ALTER TABLE tennis_match RENAME INDEX fk_match_winner TO IDX_7510D1775DFCD4B8');
    }

    public function down(Schema $schema): void
    {
        // this down() migration is auto-generated, please modify it to your needs
        $this->addSql('ALTER TABLE player DROP tour, CHANGE birth_date birth_date DATE DEFAULT NULL');
        $this->addSql('ALTER TABLE player RENAME INDEX uniq_98197a65b445906b TO uniq_player_external_ref');
        $this->addSql('ALTER TABLE prediction CHANGE computed_at computed_at DATETIME NOT NULL');
        $this->addSql('ALTER TABLE prediction RENAME INDEX uniq_36396fc82abeacd6 TO uniq_prediction_match');
        $this->addSql('ALTER TABLE prediction RENAME INDEX idx_36396fc853f6604d TO fk_prediction_favorite');
        $this->addSql('ALTER TABLE app_user CHANGE id id CHAR(36) NOT NULL, CHANGE created_at created_at DATETIME NOT NULL');
        $this->addSql('DROP INDEX UNIQ_7510D177B445906B ON tennis_match');
        $this->addSql('ALTER TABLE tennis_match DROP external_ref, CHANGE scheduled_at scheduled_at DATETIME NOT NULL');
        $this->addSql('CREATE INDEX idx_match_scheduled_at ON tennis_match (scheduled_at)');
        $this->addSql('ALTER TABLE tennis_match RENAME INDEX idx_7510d1778b71ac85 TO idx_match_player_b');
        $this->addSql('ALTER TABLE tennis_match RENAME INDEX idx_7510d17799c4036b TO idx_match_player_a');
        $this->addSql('ALTER TABLE tennis_match RENAME INDEX idx_7510d1775dfcd4b8 TO fk_match_winner');
        $this->addSql('ALTER TABLE refresh_token RENAME INDEX uniq_c74f2195c74f2195 TO uniq_refresh_token');
        $this->addSql('ALTER TABLE subscription CHANGE user_id user_id CHAR(36) NOT NULL, CHANGE current_period_end current_period_end DATETIME DEFAULT NULL, CHANGE created_at created_at DATETIME NOT NULL, CHANGE canceled_at canceled_at DATETIME DEFAULT NULL');
        $this->addSql('ALTER TABLE subscription RENAME INDEX idx_a3c664d3a76ed395 TO idx_subscription_user');
        $this->addSql('ALTER TABLE subscription RENAME INDEX idx_a3c664d3e899029b TO fk_subscription_plan');
        $this->addSql('ALTER TABLE plan RENAME INDEX uniq_dd5a5b7d77153098 TO uniq_plan_code');
    }
}
