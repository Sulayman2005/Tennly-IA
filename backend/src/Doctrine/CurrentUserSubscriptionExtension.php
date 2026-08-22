<?php

namespace App\Doctrine;

use ApiPlatform\Doctrine\Orm\Extension\QueryCollectionExtensionInterface;
use ApiPlatform\Doctrine\Orm\Util\QueryNameGeneratorInterface;
use ApiPlatform\Metadata\Operation;
use App\Entity\Subscription;
use App\Entity\User;
use Doctrine\ORM\QueryBuilder;
use Symfony\Bundle\SecurityBundle\Security;

/**
 * Referme la faille IDOR sur GET /api/subscriptions : la sécurité déclarée sur
 * l'opération (`is_granted('ROLE_USER')`, voir Subscription::class) autorise
 * n'importe quel utilisateur connecté à lister la collection, mais sans
 * filtre applicatif elle renverrait les abonnements de TOUS les
 * utilisateurs — n'importe qui pourrait alors voir la formule et le statut
 * d'abonnement d'un autre compte (identifiants Stripe compris).
 *
 * Cette extension restreint la collection aux abonnements du user courant ;
 * un ROLE_ADMIN garde une vue complète (utile pour le futur back-office admin,
 * cahier des charges section 3.10).
 */
final class CurrentUserSubscriptionExtension implements QueryCollectionExtensionInterface
{
    public function __construct(private readonly Security $security)
    {
    }

    public function applyToCollection(
        QueryBuilder $queryBuilder,
        QueryNameGeneratorInterface $queryNameGenerator,
        string $resourceClass,
        ?Operation $operation = null,
        array $context = [],
    ): void {
        if (Subscription::class !== $resourceClass) {
            return;
        }

        if ($this->security->isGranted('ROLE_ADMIN')) {
            return;
        }

        $user = $this->security->getUser();

        if (!$user instanceof User) {
            // Ne devrait pas arriver : l'opération exige déjà ROLE_USER. On
            // renvoie une collection vide plutôt que de laisser passer une
            // requête sans utilisateur identifiable.
            $queryBuilder->andWhere('1 = 0');

            return;
        }

        $rootAlias = $queryBuilder->getRootAliases()[0];

        $queryBuilder
            ->andWhere(sprintf('%s.user = :current_user', $rootAlias))
            ->setParameter('current_user', $user->getId());
    }
}
