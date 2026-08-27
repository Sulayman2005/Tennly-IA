<script setup>
// Petit badge "ATP"/"WTA" — sert uniquement à distinguer visuellement les
// deux circuits dans l'interface (voir ml-service/import_real_data.py et
// import_upcoming_matches.py pour la donnée elle-même, colonne player.tour).
// Un match n'oppose jamais un joueur ATP à une joueuse WTA (deux pools Elo
// totalement séparés), donc ce badge est purement informatif ici, jamais
// utilisé pour filtrer quoi que ce soit.
defineProps({
  tour: { type: String, required: true }, // 'atp' | 'wta'
  // À activer sur un fond déjà coloré/sombre (ex. MatchCard, dégradé vert) —
  // sinon les teintes bleu/rose ci-dessous deviennent illisibles.
  onDark: { type: Boolean, default: false },
})
</script>

<template>
  <span
    class="tour-badge"
    :class="[tour === 'wta' ? 'wta' : 'atp', { 'on-dark': onDark }]"
  >{{ tour === 'wta' ? 'WTA' : 'ATP' }}</span>
</template>

<style scoped>
.tour-badge {
  display: inline-flex;
  align-items: center;
  padding: 1px 7px;
  border-radius: 999px;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.03em;
  line-height: 1.6;
}
.tour-badge.atp {
  background: rgba(0, 113, 227, 0.14);
  color: var(--blue);
}
.tour-badge.wta {
  background: rgba(217, 70, 160, 0.14);
  color: #d946a0;
}
.tour-badge.on-dark {
  background: rgba(255, 255, 255, 0.18);
  color: #fff;
}
</style>