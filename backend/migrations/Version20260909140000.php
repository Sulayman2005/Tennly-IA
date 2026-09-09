<?php

declare(strict_types=1);

namespace DoctrineMigrations;

use Doctrine\DBAL\Schema\Schema;
use Doctrine\Migrations\AbstractMigration;

/**
 * Élargit player.photo_url de VARCHAR(255) à VARCHAR(500) : les URLs de
 * miniatures Wikimedia (voir ml-service/import_player_photos_wikipedia.py)
 * dépassent 255 caractères dès que le nom du joueur contient des caractères
 * accentués percent-encodés (le nom de fichier apparaît deux fois dans le
 * chemin /thumb/.../330px-...). Incident réel en prod le 09/09/2026 :
 * DataError "Data too long for column 'photo_url'" sur Ben Shelton, qui a
 * interrompu l'import après seulement 5 joueurs sur 56.
 */
final class Version20260909140000 extends AbstractMigration
{
    public function getDescription(): string
    {
        return "Élargit player.photo_url à VARCHAR(500) (URLs Wikimedia trop longues pour 255).";
    }

    public function up(Schema $schema): void
    {
        $this->addSql('ALTER TABLE player MODIFY photo_url VARCHAR(500) DEFAULT NULL');
    }

    public function down(Schema $schema): void
    {
        $this->addSql('ALTER TABLE player MODIFY photo_url VARCHAR(255) DEFAULT NULL');
    }
}
