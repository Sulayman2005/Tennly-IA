<?php

namespace App\Entity\Enum;

/**
 * Surfaces de jeu — utilisées pour le calcul de l'Elo par surface (cahier des
 * charges section 4.4.2, feature n°1).
 */
enum Surface: string
{
    case DUR = 'dur';
    case TERRE_BATTUE = 'terre_battue';
    case GAZON = 'gazon';
    case INDOOR = 'indoor';
}
