<script setup>
import { RouterLink } from 'vue-router'

// Politique de confidentialité — RGPD (Règlement UE 2016/679) + loi
// Informatique et Libertés. Décrit les traitements réellement en place dans
// le code (compte utilisateur, abonnement Stripe, JWT) plutôt qu'une liste
// générique : pas de mention d'un traitement qui n'existe pas.
</script>

<template>
  <div class="legal">
    <h1>Politique de confidentialité</h1>
    <p class="updated">Dernière mise à jour : [date à compléter]</p>

    <section>
      <h2>Responsable du traitement</h2>
      <p>
        [Nom commercial / raison sociale — à compléter], éditeur du site Tennly IA — voir les
        <RouterLink to="/mentions-legales">mentions légales</RouterLink> pour l'identité complète. Contact pour toute
        question relative à vos données : [email de contact — à compléter].
      </p>
    </section>

    <section>
      <h2>Quelles données nous collectons, et pourquoi</h2>
      <div class="table-scroll">
        <table class="data-table">
          <thead>
            <tr>
              <th>Donnée</th>
              <th>Finalité</th>
              <th>Base légale</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>Email, prénom, nom, mot de passe (haché)</td>
              <td>Création et gestion de ton compte</td>
              <td>Exécution du contrat</td>
            </tr>
            <tr>
              <td>Statut et historique d'abonnement</td>
              <td>Donner accès aux analyses complètes si tu es abonné</td>
              <td>Exécution du contrat</td>
            </tr>
            <tr>
              <td>Données de paiement (carte, etc.)</td>
              <td>Traitement du paiement de l'abonnement</td>
              <td>Exécution du contrat — voir "Stripe" ci-dessous : nous ne stockons jamais ces données nous-mêmes</td>
            </tr>
            <tr>
              <td>Mesure d'audience (si tu acceptes les cookies analytiques)</td>
              <td>Comprendre l'usage du site pour l'améliorer</td>
              <td>Consentement</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section>
      <h2>Qui reçoit ces données</h2>
      <p>
        <b>Stripe</b> (prestataire de paiement) traite directement les données de carte bancaire lors du paiement
        d'un abonnement — notre serveur ne les voit ni ne les stocke jamais. Stripe agit comme sous-traitant au sens
        du RGPD ; ses propres engagements de conformité sont disponibles sur stripe.com/fr/privacy.
      </p>
      <p>
        [Hébergeur — à compléter] héberge la base de données et l'application une fois le site mis en ligne. Ces
        données ne sont partagées avec aucun autre tiers, et ne sont jamais vendues.
      </p>
      <p>
        Si un outil de mesure d'audience est activé (voir bannière cookies), celui-ci recevra des données de
        navigation anonymisées ou pseudonymisées, uniquement si tu y as consenti.
      </p>
    </section>

    <section>
      <h2>Durée de conservation</h2>
      <p>
        Les données de ton compte sont conservées tant que ton compte est actif. Si tu supprimes ton compte ou nous
        demandes leur effacement, elles sont supprimées sous un délai raisonnable, sous réserve des durées de
        conservation légales (notamment comptables, en cas de paiement effectué).
      </p>
    </section>

    <section>
      <h2>Tes droits</h2>
      <p>
        Conformément au RGPD, tu disposes d'un droit d'accès, de rectification, d'effacement, de limitation, de
        portabilité et d'opposition sur tes données personnelles. Tu peux exercer ces droits en écrivant à
        [email de contact — à compléter]. Tu peux également déposer une réclamation auprès de la CNIL
        (<a href="https://www.cnil.fr" target="_blank" rel="noopener">cnil.fr</a>) si tu estimes que tes droits ne
        sont pas respectés.
      </p>
    </section>

    <section>
      <h2>Sécurité</h2>
      <p>
        Les mots de passe sont stockés hachés, jamais en clair. L'authentification utilise des jetons (JWT) à durée
        de vie limitée. Le site doit être servi en HTTPS une fois en ligne, pour chiffrer les échanges entre ton
        navigateur et nos serveurs.
      </p>
    </section>

    <section>
      <h2>Cookies</h2>
      <p>
        Voir le détail des cookies utilisés et la gestion de ton consentement via la bannière affichée en bas de
        page, ou en réinitialisant ton choix depuis les paramètres de ton navigateur.
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

.table-scroll {
  overflow-x: auto;
  margin-top: 10px;
}

.data-table {
  width: 100%;
  min-width: 480px;
  border-collapse: collapse;
  font-size: 13px;
}

.data-table th {
  text-align: left;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.02em;
  color: var(--grey);
  padding: 8px 10px;
  border-bottom: 1px solid var(--line);
}

.data-table td {
  padding: 10px;
  border-bottom: 1px solid var(--line);
  vertical-align: top;
  line-height: 1.5;
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