<?php

return [
    Symfony\Bundle\FrameworkBundle\FrameworkBundle::class => ['all' => true],
    Doctrine\Bundle\DoctrineBundle\DoctrineBundle::class => ['all' => true],
    Doctrine\Bundle\MigrationsBundle\DoctrineMigrationsBundle::class => ['all' => true],
    ApiPlatform\Symfony\Bundle\ApiPlatformBundle::class => ['all' => true],
    Lexik\Bundle\JWTAuthenticationBundle\LexikJWTAuthenticationBundle::class => ['all' => true],
    Gesdinet\JWTRefreshTokenBundle\GesdinetJWTRefreshTokenBundle::class => ['all' => true],
    Nelmio\CorsBundle\NelmioCorsBundle::class => ['all' => true],
    Symfony\Bundle\SecurityBundle\SecurityBundle::class => ['all' => true],
    Symfony\Bundle\MakerBundle\MakerBundle::class => ['dev' => true],
    Symfony\Bundle\TwigBundle\TwigBundle::class => ['all' => true],
    // Enregistré à la main : composer.json a "allow-contrib": false (voir ce
    // fichier), donc Symfony Flex n'exécute jamais la recette de
    // sentry/sentry-symfony (recette "contrib", pas officielle) — sans cette
    // ligne, le bundle serait installé par Composer mais jamais activé, et
    // le SENTRY_DSN de config/packages/sentry.yaml resterait sans effet.
    Sentry\SentryBundle\SentryBundle::class => ['all' => true],
];
