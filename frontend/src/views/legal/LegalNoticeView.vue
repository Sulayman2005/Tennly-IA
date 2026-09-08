<script setup>
import { RouterLink } from 'vue-router'

// Mentions légales — obligatoires (loi n°2004-575 "LCEN", art. 6-III).
// Les champs entre crochets [ ] doivent être complétés avant toute mise en
// ligne publique réelle : à ce stade, le projet n'a pas encore de statut
// juridique déclaré (auto-entreprise, société...), donc ces informations
// n'existent tout simplement pas encore — plutôt que d'inventer un SIRET ou
// une adresse, ils restent volontairement des champs à remplir.
</script>

<template>
  <div class="legal">
    <h1>Mentions légales</h1>
    <p class="updated">Dernière mise à jour : [date à compléter]</p>

    <section>
      <h2>Éditeur du site</h2>
      <p>
        Le site Tennly est édité par [nom commercial / raison sociale — à compléter], [forme juridique — à
        compléter : auto-entrepreneur, SASU, EURL...], immatriculé(e) sous le numéro SIRET [SIRET — à compléter],
        dont le siège est situé [adresse du siège — à compléter].
      </p>
      <p>
        Directeur de la publication : [nom du responsable de publication — à compléter].<br />
        Contact : [email de contact — à compléter].
      </p>
      <p class="note">
        Tant que ce statut n'est pas déclaré, le site ne doit pas être ouvert à de vrais paiements ni à un public
        autre que des tests internes — ces informations sont légalement obligatoires dès qu'un service payant est
        proposé au public en France.
      </p>
    </section>

    <section>
      <h2>Hébergement</h2>
      <p>
        Le site est actuellement hébergé en local, sur l'environnement de développement de l'éditeur — aucune mise en
        ligne publique n'est effective à ce stade. Les coordonnées de l'hébergeur (nom, adresse, contact) seront
        ajoutées ici dès qu'un hébergement de production sera choisi.
      </p>
    </section>

    <section>
      <h2>Propriété intellectuelle</h2>
      <p>
        L'ensemble des contenus présents sur le site (textes, analyses, visuels, code source, logo) est protégé par
        le droit de la propriété intellectuelle. Toute reproduction, représentation ou exploitation, totale ou
        partielle, sans autorisation préalable est interdite.
      </p>
    </section>

    <section>
      <h2>Données personnelles</h2>
      <p>
        Le traitement des données personnelles est détaillé dans notre
        <RouterLink to="/confidentialite">politique de confidentialité</RouterLink>.
      </p>
    </section>

    <section>
      <h2>Nature du service</h2>
      <p>
        Tennly propose des analyses statistiques et des estimations de probabilité à visée informative et
        pédagogique sur des rencontres de tennis. Ce n'est ni un service de paris sportifs, ni un service de
        pronostics garantissant un résultat ou un gain — voir nos
        <RouterLink to="/cgu">conditions générales d'utilisation</RouterLink>.
      </p>
    </section>
  </div>
</template>

<style scoped>
.legal {
  max-width: 720px;
  margin: 0 auto;
  padding: 48px 0 80px;
}

h1 {
  font-size: 30px;
  margin-bottom: 6px;
}

.updated {
  font-size: 12px;
  color: var(--grey);
  margin-bottom: 32px;
}

section {
  margin-bottom: 28px;
}

section h2 {
  font-size: 17px;
  margin-bottom: 8px;
}

section p {
  font-size: 14px;
  line-height: 1.7;
  color: var(--ink);
  margin: 0 0 10px;
}

.note {
  font-size: 12px;
  color: var(--grey);
  font-style: italic;
}

@media (max-width: 480px) {
  .legal {
    padding: 32px 0 60px;
  }
  h1 {
    font-size: 23px;
  }
}
</style>