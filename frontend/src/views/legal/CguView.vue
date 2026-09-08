<script setup>
import { RouterLink } from 'vue-router'

// Conditions Générales d'Utilisation — régissent l'usage du site en général
// (navigation, compte gratuit), par opposition aux CGV qui régissent
// spécifiquement l'abonnement payant.
</script>

<template>
  <div class="legal">
    <h1>Conditions générales d'utilisation</h1>
    <p class="updated">Dernière mise à jour : [date à compléter]</p>

    <section>
      <h2>1. Objet</h2>
      <p>
        Les présentes conditions régissent l'accès et l'utilisation du site Tennly, accessible à l'adresse
        [nom de domaine — à compléter]. En créant un compte ou en utilisant le site, tu acceptes ces conditions dans
        leur intégralité.
      </p>
    </section>

    <section>
      <h2>2. Nature du service — ce que Tennly n'est pas</h2>
      <p>
        Tennly propose des analyses statistiques de matchs de tennis, calculées à partir de données réelles
        (historique ATP, Elo par surface, statistiques de service/retour). Ces analyses sont fournies à titre
        <b>informatif et pédagogique</b>. Tennly n'est ni un opérateur de paris sportifs, ni un service de
        pronostics garantissant un résultat : aucune analyse, aussi fiable soit-elle statistiquement (voir notre
        <RouterLink to="/fiabilite">page de fiabilité du modèle</RouterLink>), ne prédit avec certitude l'issue d'un
        match individuel. Si tu paries sur la base de ces analyses ailleurs que sur notre site, tu le fais sous ta
        seule responsabilité.
      </p>
    </section>

    <section>
      <h2>3. Création de compte</h2>
      <p>
        La création d'un compte est gratuite et ne déclenche aucun paiement. Tu t'engages à fournir des informations
        exactes et à préserver la confidentialité de ton mot de passe. Tu es responsable de toute activité effectuée
        depuis ton compte.
      </p>
      <p>
        Tennly est réservé aux personnes majeures, ou mineures avec l'autorisation de leur représentant légal.
      </p>
    </section>

    <section>
      <h2>4. Contenu accessible selon ton statut</h2>
      <p>
        Sans abonnement, tu accèdes librement à la liste des matchs et à un aperçu de l'analyse (favori pressenti,
        niveau de confiance). L'analyse complète (comparatif détaillé, facteurs d'explication) est réservée aux
        comptes disposant d'un abonnement actif — voir nos <RouterLink to="/cgv">conditions générales de vente</RouterLink>.
      </p>
    </section>

    <section>
      <h2>5. Propriété intellectuelle</h2>
      <p>
        Le contenu du site (analyses, textes, code, visuels, marque) est protégé par le droit d'auteur et ne peut
        être reproduit, redistribué ou exploité commercialement sans autorisation écrite préalable.
      </p>
    </section>

    <section>
      <h2>6. Responsabilité</h2>
      <p>
        Tennly met tout en œuvre pour la fiabilité de ses analyses, mais ne garantit ni leur exactitude absolue ni
        un quelconque résultat. L'éditeur ne saurait être tenu responsable des décisions prises par un utilisateur sur
        la base des analyses fournies, y compris en cas de perte financière résultant d'un pari effectué ailleurs.
      </p>
    </section>

    <section>
      <h2>7. Suspension et résiliation</h2>
      <p>
        Tennly se réserve le droit de suspendre ou clôturer un compte en cas d'usage frauduleux, de non-respect
        des présentes conditions, ou de tentative de contournement du service.
      </p>
    </section>

    <section>
      <h2>8. Droit applicable</h2>
      <p>
        Les présentes conditions sont soumises au droit français. En cas de litige, une solution amiable sera
        recherchée avant toute action judiciaire.
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

@media (max-width: 480px) {
  .legal {
    padding: 32px 0 60px;
  }
  h1 {
    font-size: 23px;
  }
}
</style>