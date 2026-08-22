<?php

namespace App\State;

use ApiPlatform\Metadata\Operation;
use ApiPlatform\State\ProviderInterface;
use App\Entity\User;
use Symfony\Bundle\SecurityBundle\Security;

/**
 * Fournit la ressource pour GET /api/me : renvoie toujours l'utilisateur de
 * la requête en cours (jamais un id passé en paramètre), donc il n'y a
 * structurellement aucun moyen d'utiliser cette route pour lire le compte de
 * quelqu'un d'autre.
 *
 * @implements ProviderInterface<User>
 */
final class CurrentUserProvider implements ProviderInterface
{
    public function __construct(private readonly Security $security)
    {
    }

    public function provide(Operation $operation, array $uriVariables = [], array $context = []): ?User
    {
        $user = $this->security->getUser();

        return $user instanceof User ? $user : null;
    }
}
