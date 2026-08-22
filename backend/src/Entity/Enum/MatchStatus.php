<?php

namespace App\Entity\Enum;

enum MatchStatus: string
{
    case SCHEDULED = 'scheduled';
    case LIVE = 'live';
    case FINISHED = 'finished';
    case WALKOVER = 'walkover';
}
