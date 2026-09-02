<script setup>
import { RouterLink } from 'vue-router'

// Conditions Générales de Vente — encadrent spécifiquement l'abonnement
// payant (Classique mensuel, VIP trimestriel, VIP annuel — voir Plan::class
// côté backend). Les tarifs ne sont jamais recopiés ici en dur : ils
// changent potentiellement, et la seule source fiable est la page
// d'abonnement au moment de l'achat (cohérent avec le principe "aucune
// donnée n'est inventée" du reste du projet).
</script>

<template>
  <div class="legal">
    <h1>Conditions générales de vente</h1>
    <p class="updated">Dernière mise à jour : [date à compléter]</p>

    <p class="warning">
      ⚠️ Avant toute ouverture au public avec de vrais paiements, ces CGV doivent être relues par un professionnel du
      droit — en particulier les clauses de rétractation et de médiation ci-dessous, qui ont des conséquences légales
      réelles si elles sont mal formulées.
    </p>

    <section>
      <h2>1. Objet et formules</h2>
      <p>
        Les présentes CGV s'appliquent à la souscription d'un abonnement Tennly IA, quelle que soit la formule
        choisie (Classique, VIP, VIP annuel). Le prix et la périodicité exacts de chaque formule sont ceux affichés
        sur la page d'abonnement au moment de la souscription — ils ne sont pas reproduits ici pour éviter tout écart
        avec le tarif réellement appliqué.
      </p>
    </section>

    <section>
      <h2>2. Paiement</h2>
      <p>
        Le paiement est traité par Stripe, prestataire de paiement tiers. Tennly IA ne stocke jamais tes coordonnées
        bancaires. L'abonnement est prélevé automatiquement à chaque échéance (mensuelle, trimestrielle ou annuelle
        selon la formule) jusqu'à résiliation.
      </p>
    </section>

    <section>
      <h2>3. Durée et reconduction</h2>
      <p>
        L'abonnement est reconduit tacitement à chaque échéance, sauf résiliation de ta part avant la date de
        renouvellement. Tu peux résilier à tout moment depuis ton espace personnel ; la résiliation prend effet à la
        fin de la période déjà payée — pas de remboursement au prorata de la période en cours.
      </p>
    </section>

    <section>
      <h2>4. Droit de rétractation</h2>
      <p>
        Conformément à l'article L221-28 13° du Code de la consommation, le droit de rétractation de 14 jours ne
        s'applique pas aux contenus numériques dont l'exécution a commencé avec ton accord exprès et ta renonciation
        expresse à ce droit. Concrètement : en souscrivant, tu obtiens un accès immédiat aux analyses complètes, et il
        te sera demandé, au moment du paiement, de confirmer explicitement que tu souhaites un accès immédiat et que
        tu renonces en conséquence à ton droit de rétractation.
      </p>
      <p class="note">
        Point d'action produit (pas seulement légal) : cette confirmation explicite doit exister comme une case à
        cocher séparée au moment du paiement — actuellement le parcours de paiement ne l'implémente pas encore. Sans
        cette case, le droit de rétractation de 14 jours s'applique de plein droit, ce qui n'est probablement pas ce
        que tu souhaites pour un service à accès immédiat.
      </p>
    </section>

    <section>
      <h2>5. Remboursement</h2>
      <p>
        Hors exercice du droit de rétractation ci-dessus, les sommes versées pour une période d'abonnement déjà
        entamée ne sont pas remboursables, sauf disposition légale contraire ou geste commercial exceptionnel décidé
        au cas par cas.
      </p>
    </section>

    <section>
      <h2>6. Réclamation et médiation</h2>
      <p>
        Pour toute réclamation, contacte [email de contact — à compléter]. Conformément à l'article L616-1 du Code de
        la consommation, si aucune solution amiable n'est trouvée, tu peux recourir gratuitement à un médiateur de la
        consommation — [nom et coordonnées du médiateur — à désigner]. Cette désignation est obligatoire dès lors que
        de vrais paiements de consommateurs sont acceptés.
      </p>
    </section>

    <section>
      <h2>7. Droit applicable</h2>
      <p>
        Les présentes CGV sont soumises au droit français. Voir aussi nos
        <RouterLink to="/cgu">conditions générales d'utilisation</RouterLink> pour les règles d'usage général du site.
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
  margin-bottom: 20px;
}

.warning {
  background: #fff8e6;
  border: 1px solid #f0d98c;
  border-radius: 12px;
  padding: 14px 18px;
  font-size: 13px;
  line-height: 1.6;
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
  .warning {
    padding: 12px 14px;
  }
}
</style>