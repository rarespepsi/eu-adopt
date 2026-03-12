# Regulă: Adăpost public – BONUS pe animale

## Condiție
Când organizația (ONG/firmă) are bifat **„Sunt adăpost public”**, toți câinii (animalele) postați de ei intră în această regulă.

## Afișare
1. **Pe poza animalului**  
   - Să apară un **badge „BONUS!”** (vizibil pe imagine).
2. **La click pe badge**  
   - Să apară o **notă / tooltip / popover** cu textul:
   - *„Sterilizat / cip / vaccin și carnet de sănătate. Aceste servicii sunt gratuite!”*

## Implementare tehnică (când se face)
- În cardul de animal (ex. `pt_p2_card.html` sau echivalent):  
  - dacă `pet.from_public_shelter` (sau echivalent din backend) este adevărat, afișează badge-ul „BONUS!” peste poză.
- La click pe badge: deschide un popover/modal cu textul de mai sus.
- Backend: la listarea animalelor, pune `from_public_shelter = True` pentru animalele care aparțin unui user ONG cu `is_public_shelter = True`.

## Notă
Pagina PT este înghețată; modificările pe card se fac după ce se dă parola și se cere explicit implementarea.
