<?php

namespace App\Entity\Enum;

/**
 * Niveau de confiance affiché sur chaque carte de match (cahier des charges
 * section 3.2 : "faible / moyen / élevé").
 */
enum ConfidenceLevel: string
{
    case FAIBLE = 'faible';
    case MOYEN = 'moyen';
    case ELEVE = 'eleve';
}
