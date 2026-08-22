<?php

namespace App\Entity\Enum;

/**
 * Périodicité de facturation d'une formule (cahier des charges section 3.2.1 :
 * Classique = mensuel, VIP = trimestriel, VIP annuel = annuel).
 */
enum BillingPeriod: string
{
    case MONTH = 'month';
    case QUARTER = 'quarter';
    case YEAR = 'year';
}
