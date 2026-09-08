<?php
declare(strict_types=1);

namespace DoctrineMigrations;

use Doctrine\DBAL\Schema\Schema;
use Doctrine\Migrations\AbstractMigration;

/**
 * Insère les 3 formules d'abonnement réelles (Classique/Premium/Premium
 * annuel) avec leurs identifiants de prix Stripe (mode Test), pour
 * remplacer les données de seed_dev_data.sql (codes différents : vip/
 * vip-annuel, sans stripe_price_id) qui n'avaient jamais été rejouées ici.
 * Sans cette ligne en base, POST /api/checkout-sessions échoue toujours
 * avec "Formule inconnue." (voir CheckoutSessionController::__invoke) —
 * bug diagnostiqué et corrigé le 08/09/2026.
 */
final class Version20260908183000 extends AbstractMigration
{
    public function getDescription(): string
    {
        return 'Insère les formules Classique/Premium/Premium annuel avec leurs stripe_price_id réels';
    }

    public function up(Schema $schema): void
    {
        $this->addSql(
            "INSERT INTO plan (code, name, price_cents, currency, billing_period, stripe_price_id, active) VALUES " .
            "('classique', 'Classique', 999, 'EUR', 'month', 'price_1UBcS4D3JHRelVGMoqGiklSm', 1), " .
            "('premium', 'Premium', 4999, 'EUR', 'quarter', 'price_1UBcT2D3JHRelVGMvAqDZ1Bg', 1), " .
            "('premium-annuel', 'Premium annuel', 9999, 'EUR', 'year', 'price_1UBcU1D3JHRelVGM0xeexvD3', 1)"
        );
    }

    public function down(Schema $schema): void
    {
        $this->addSql("DELETE FROM plan WHERE code IN ('classique', 'premium', 'premium-annuel')");
    }
}
