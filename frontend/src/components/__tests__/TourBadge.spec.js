import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import TourBadge from '../TourBadge.vue'

// Ce test couvre le côté frontend du bug du 28/08/2026 : quand `tour`
// n'arrivait pas de l'API (propriété manquante côté entité Player), ce
// composant retombait silencieusement sur "ATP" sans que rien ne signale
// l'anomalie. On fixe ici le comportement attendu dans les deux cas, plus
// le cas "valeur absente" qui a effectivement causé le bug en prod — voir
// aussi backend/tests/Entity/PlayerTest.php pour le côté API.
describe('TourBadge', () => {
  it('affiche "WTA" et la classe .wta quand tour vaut "wta"', () => {
    const wrapper = mount(TourBadge, { props: { tour: 'wta' } })

    expect(wrapper.text()).toBe('WTA')
    expect(wrapper.classes()).toContain('wta')
    expect(wrapper.classes()).not.toContain('atp')
  })

  it('affiche "ATP" et la classe .atp quand tour vaut "atp"', () => {
    const wrapper = mount(TourBadge, { props: { tour: 'atp' } })

    expect(wrapper.text()).toBe('ATP')
    expect(wrapper.classes()).toContain('atp')
    expect(wrapper.classes()).not.toContain('wta')
  })

  it('n\'applique la classe .on-dark que si onDark est explicitement demandé', () => {
    const clair = mount(TourBadge, { props: { tour: 'wta' } })
    const sombre = mount(TourBadge, { props: { tour: 'wta', onDark: true } })

    expect(clair.classes()).not.toContain('on-dark')
    expect(sombre.classes()).toContain('on-dark')
  })
})