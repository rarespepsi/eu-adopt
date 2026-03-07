# ⚠️ FIȘIER VECHI – CONȚINUT CENTRALIZAT

**📚 Acest fișier a fost centralizat în `DOCUMENTATIE_CENTRALIZATA.md`**  
**Nu mai actualiza acest fișier – folosește fișierul centralizat pentru a evita duplicarea informațiilor.**

---

# Adopt a Pet – Wish list & viziune site

Document de lucru: tot ce concluzionăm legat de viziunea și direcția site-ului rămâne notat aici.

---

## Context / de ce există proiectul

- Fondatorul a fost **director la un adăpost public de câini din România**.
- **Realitatea din teren**: în România sunt multe padocuri (de stat sau private) care **nu au publicitate la adopție în adevăratul sens al cuvântului** – animalele există, dar nu sunt promovate cum trebuie.
- **Problema principală**: promovarea animalelor din adăpost pentru adopție – doar Facebook odată nu era suficient (vizibilitate limitată, un singur post, nu un „catalog” persistent).
- Site-ul vizează să rezolve asta: un loc unde animalele să fie promovate **continuu**, vizibile, ușor de găsit și de partajat – pentru orice adăpost care vrea să iasă din invizibilitate.
- **Obiectiv**: **centralizarea tuturor câinilor din țară dați spre adopție** – un singur punct unde adoptatorul poate vedea oferta din toate adăposturile.
- **Realitate**: mare parte din câinii dați spre adopție **nu sunt de rasă** – sunt **metiși / maidanezi**. Site-ul trebuie să reflecte asta (câmp rasă: Metis, Maidanez, eventual „mix” sau rase doar opțional), nu un catalog de rase pure.

---

## Ce există acum (baza)

- Django 6, app `anunturi`
- Model **Pet**: nume, rasă, tip (câine/pisică *– de extins la* **altele**: păsări, magari, etc.), vârstă, sex, mărime, descriere, imagine, status (adoptable / pending / adopted), tags
- Pagini: home, listă animale (`pets-all`), pagină animal (`pets/<id>/`), admin Django

---

## Clienți / public țintă

**Clienții** site-ului (membri care postează animale) sunt două categorii:

1. **Adăposturi din România** – publice sau private. Postează animalele din adăpost; devin membri ai platformei.
2. **Asociații de profil** – asociații cu profil (protecția animalelor, adopții, etc.). La fel, devin membri și postează animalele pe care le au în grijă.

Ambele tipuri sunt **clienți** – se înscriu ca membri, respectă regulile (control, date medicale, validare imagini, etc.) și pot fi taxate după perioada gratuită.

**Beneficiari** (nu plătesc, dar folosesc site-ul): **adoptatorii** – persoane care caută un animal, folosesc filtre, descrieri, poze, link de partajat.

**Persoane fizice** – încă neclar cum le tratăm. Sunt oameni care nu sunt nici adăpost, nici asociație (ex. au găsit un maidanez, se mută și nu îl pot lua, au 1–2 animale de dat spre adopție). Opțiuni de luat în calcul:
- **Nu le permitem la început** – doar adăposturi + asociații; persoane fizice poate mai târziu, cu reguli clare.
- **Le permitem cu limită strictă** – ex. max 1–3 animale per persoană, sau doar „anunțuri ocazionale”; verificare mai atentă („la grămadă” obligatoriu).
- **Le permitem ca a treia categorie de membru** – tip cont „Persoană fizică”, cu limite și eventual taxare diferită față de adăposturi/asociații.
- **Doar prin partener** – ex. persoana fizică pune anunțul prin intermediul unei asociații/adăpost partener (nu cont propriu).

*Decizie de luat după ce stabilim bine fluxul pentru adăposturi și asociații.*

**De ce e mai dificil cu persoanele fizice:** nu au **istoric** sau **binitate** (credibilitate / track record); nu au **transport**, nu au **cazare**; de obicei sunt unii care **umplu Facebookul** cu tot felul de postări (câini pe câmp, etc.). E o discuție mai strategică/operațională – dar amândoi vom găsi o metodă. Dacă e prea diferită de partea tehnică, temele deschise sunt notate separat mai jos (întrebări pentru ChatGPT / discuție separată).

---

## Model membri – listă de membri, gratuit / plătit

- **Liste de membri**: **clienții** sunt fie **adăposturi** (publice/private), fie **asociații de profil**. Ex.: Adăpostul din Cluj, Asociația X Brașov etc. devin membri și pot posta animalele lor.
- **Primele 6 luni: 100% gratuit** – nu se așteaptă clienți din prima; perioada de lansare și creștere, fără taxe. Obiectiv: atragere adăposturi, umplere catalog.
- **După 6 luni: putem taxa** – limită gratuită (ex. până la **50 animale/lună**), peste care abonament plătit; sau alt model de monetizare de stabilit.
- **Transport asigurat de platformă (altă zonă decât adăpostul)**: bine ar fi ca **noi** (site-ul) să asigurăm transportul când adoptatorul e în altă zonă decât adăpostul. **Trebuie să mâncăm și o felie din partea asta de bani** – platforma ia un procent/comision din suma pentru transport (sursă de venit în plus față de abonamentul membrilor).
- **Bandou de reclame** – **reclame ale producătorilor de mâncare** (pentru animale), produse pentru animale, servicii veterinare, etc. – **legate de animale**. Zone dedicate pe site (banner-uri) unde afișăm reclame de parteneri/sponsori din domeniu; sursă de venit și conținut relevant pentru vizitatori (adoptatori, iubitori de animale).
- Rezultat: fiecare client (adăpost sau asociație de profil) e un membru care postează propriile animale; site-ul devine catalogul centralizat al tuturor acestor membri; la transport între zone, platforma intermediază și își păstrează o parte din sumă; bandouri de reclame (mâncare, produse, etc.) aduc venit suplimentar.

---

## Control și verificare postări (per membru)

*Toate astea le putem numi **la grămadă**: tehnice, de imagine, validări, date medicale, condiții adopție – adică tot pachetul de verificare și control al postărilor.*

- **Control intern de verificare** la fiecare membru: postările să fie verificate înainte sau după publicare – ca să nu apară conținut nepotrivit sau date false.
- **Validare imagini (script / AI)**: recunoașterea animalului din poză – să **nu se accepte avioane, obiecte sau altceva** în loc de animal; doar poze cu câine/pisică (sau alt animal adoptabil). Poate fi un script care detectează prezența unui animal în imagine; dacă nu e animal, postarea e respinsă sau trimisă la revizie.
- **Date medicale obligatorii**: anumite câmpuri obligatorii pentru fiecare animal – starea de sănătate, vaccinuri, tratamente, etc., conform condițiilor de adopție.
- **Condiții de adopție (adăposturi publice)**: adopțiile din adăposturile publice sunt **gratuite** – animalul trebuie să îndeplinească condiții clare: **sterilizat**, **cipat**, **microcipat**, etc. Site-ul trebuie să permită (și eventual să verifice) aceste informații: câmpuri explicite (sterilizat da/nu, cipat da/nu, microcipat da/nu) și afișare clară pentru adoptator că animalul respectă condițiile.

---

## Verificare membri (onboarding) – tehnic, siguranță maximă

- **Verificare foarte bună la membri** – înainte ca un adăpost/asociație să devină membru și să poată posta, colectăm și verificăm documente și date obligatorii:
  - **Certificat de înregistrare** (organizație/adăpost/asociație) – încărcat și verificat de admin.
  - **Copie buletin administrator** – act de identitate al administratorului/reprezentantului legal; încărcat în format securizat, acces doar pentru verificare.
  - **Telefon** – număr de contact obligatoriu, eventual verificat (SMS/apel).
  - **Adresă** – obligatorie, localizată Google Maps (deja în wish list); verificare că adresa există și corespunde.
- **Siguranță maximă**: stocare securizată a documentelor (certificat, copie buletin); acces restricționat (doar admin/rol verificare); nu afișăm date sensibile pe site; conformitate cu protecția datelor (GDPR). Documentele pot fi șterse după verificare sau păstrate criptat doar pentru litigii/audit.

---

## Partea legală – juridice puternice. Nu ne asumăm problemele cu animalele adoptate

- **Obiectiv: juridice puternice** – cadru legal **solid**, clauze clare, excludere fermă a răspunderii acolo unde platforma nu poate controla (animale adoptate, acțiunile membrilor și adoptatorilor). Tot ce e legat de termeni, disclaimer, răspundere trebuie **puternic** formulat și validat de avocat.
- **Principiu:** **Noi (platforma) nu ne asumăm problemele** apărute cu animalele adoptate. **Nu putem controla animalul** – nici comportamentul lui, nici starea de sănătate după adopție, nici acțiunile adoptatorului sau ale membrului (adăpost/asociație). Platforma este doar **intermediar** (catalog, punere în legătură); contractul/relația de adopție este între **membru** (ofertant) și **adoptator**.
- **Ce trebuie făcut (nivel puternic):**
  - **Termeni și condiții** – text complet, cu **clauze de excludere a răspunderii** (limitation of liability), **disclaimer** vizibil (platforma nu răspunde pentru daune, incidente, boli, comportament animal, litigii între membru și adoptator; utilizare pe propria răspundere).
  - **Acceptare explicită** – la înregistrare (membri) și/sau la utilizarea anumitor funcții (ex. contact pentru adopție): bifă „Am citit și accept Termenii și condițiile” – ca să existe dovadă a acceptării.
  - **Pagină dedicată Termeni și condiții** + link în footer și acolo unde e relevant; eventual **scurt disclaimer pe pagină de adopție** („Platforma nu răspunde pentru …”).
  - **Formulare făcute/validate de avocat** (drept civil, contracte, răspundere) – juridice puternice înseamnă și texte redactate de specialist, nu doar generice.
- **Scop:** protecție juridică **puternică** a platformei – ca să nu fim trași la răspundere pentru ce nu putem controla (animalul adoptat, acțiunile părților).

---

## Wish list – funcționalități

### Concurs pe site – câștigător = cel cu cele mai multe distribuiri ale câinilor
- **⏳ FĂCEM LA FINAL** – după ce terminăm de așezat site-ul; nu implementăm acum. (Când citești wish list-ul, amintește-ți: concursul vine la final.)
- **Concurs pe site**: **câștigătorul** este **membrul care are cele mai multe distribuiri** (adopții) **ale câinilor** – adică clasament după numărul de câini adoptați/plasați de fiecare membru.
- **Pe pagină, un script / secțiune** în care **lăudăm membrul** cu **cele mai multe adopții** – clasament (top membri după număr de adopții de câini), evidențierea primului loc, eventual și locurile 2–3.
- **Exemple de recunoaștere / recompense** afișate sau oferite: ex. „A primit 10 saci cu mâncare!”, donații de mâncare, produse sau premii de la parteneri pentru membrii de top. Secțiunea poate afișa și ce a „câștigat” membrul (saci mâncare, etc.) ca motiv de celebrare și încurajare.
- *Implementare:* clasament calculat după numărul de **câini** (tip = câine) cu status „adopted” per membru; bloc pe home sau pagină dedicată „Top membri” / „Concurs”; opțional perioade (lunar, anual) și recompense reale (mâncare, etc.) în parteneriat cu sponsori.

### Pentru promovare (prioritate mare)
- **Link unic per animal** – ușor de partajat pe Facebook, WhatsApp, e-mail (ex: site.ro/pets/123/).
- **Filtre pe listă**: **tip animal** – **Câine**, **Pisică**, **Altele** (în „Altele” intră și alte specii: păsări, magari, etc. – sunt oameni care dau spre adopție și alte animale); plus vârstă, mărime, sex, status (adoptable/pending/adopted). Filtrarea după tip animal e obligatorie pe pagină (butoane sau dropdown: Câine | Pisică | Altele).
- **Căutare** după nume, rasă sau cuvinte din descriere.
- **Pagină animal** cu poze, descriere, tags, status – „dosar” clar pentru fiecare animal.
- **SEO** – titluri/descrieri ok ca site-ul să apară la căutări (ex: „adopție câini [oraș]”).

### Pentru membri (adăposturi și asociații de profil) – cine introduce datele
- **Conturi / membri** – Adăpostul din Cluj, Asociația X, etc. = un membru; fiecare vede și editează doar animalele ei (model „Shelter” / „Membru” / „Organizație”).
- **Verificare membri (obligatorie)**: **certificat de înregistrare**, **copie buletin administrator**, **telefon**, **adresă** – toate obligatorii; stocare securizată, **siguranță maximă** (vezi secțiunea „Verificare membri”).
- **Adresă obligatorie, localizată pe Google Maps** – fiecare membru trebuie să aibă la **detalii** **adresa** completă, **localizată pe Google Maps** (adresă validată / coordonate sau link hartă). Câmp obligatoriu la înregistrare sau la completare profil; pe pagina membrului se afișează adresa și harta (embed Google Maps sau link deschidere în Google Maps).
- **Limită gratuită** – ex. până la **50 animale postate pe lună** gratuit; peste limită, abonament plătit (logică de numărare + planuri membru).
- **Admin / panou membru** – adăugare/editare animale, poze, status (Django admin deja există; pe viitor panou dedicat pentru membru).
- **Import în bulk** – Excel/CSV cu animale, ca să nu se introducă una câte una.
- **Raport simplu** – câte animale adoptable, pending, adopted (pentru raportare/statistici); pentru membru plătit eventual și statistici avansate.

### Bandou / reclame parteneri (producători mâncare, etc.)
- **Pe site, bandou de reclame** – zone rezervate pentru **reclame ale producătorilor de mâncare** pentru animale, produse pentru animale, servicii veterinare, accesorii etc. – **tot ce e legat de animale**. Publicul (adoptatori, iubitori de animale) e relevant pentru acești advertiseri; platforma încasează (per afișare, per click sau abonament sponsor).
- *Implementare:* zone banner (sidebar, header, între liste); admin încarcă/gestionează bannere sau integrare cu rețele de reclame (ex. Google AdSense cu tematică pets); politică clară: doar reclame legate de animale (mâncare, îngrijire, veterinar, etc.), fără conținut nepotrivit.

### Integrări / partajare
- **Partajare în 1 click** – butoane Share pentru Facebook, WhatsApp (link-ul către pagina animalului).
- (Opțional) **Export / preview pentru post Facebook** – text + link generat automat pentru copiat în post.

### Facilități / servicii de afișat pe pagină (tehnic)
Pe pagină (per membru sau per animal) să apară și **alte facilități** pe care membrii le oferă:
- **Transport** – ofertantul/adăpostul asigură transport (ex. până la adoptator sau pentru preluare).
- **Transport în altă zonă – asigurat de platformă**: când adoptatorul e în **altă zonă** decât adăpostul, **platforma** (noi) asigură transportul; platforma ia **o felie din banii pentru transport** (comision/procent) – sursă de venit.
- **Preluare de la ofertant în cabinet veterinar și supunere la analize** – animalul poate fi preluat la un cabinet veterinar, unde se fac analize etc.
- **Transportul câinilor către adoptator** – livrare/transport al câinelui până la adoptator (fie de la membru, fie prin platformă când e altă zonă).
- **Listă de transportatori** – **lista transportatorilor** din **diferite zone din țară** (național) și **internațional**. Platforma păstrează o bază de transportatori (nume, zone acoperite, contact, tarife sau tip ofertă); când se oferă transport în altă zonă, se alege/atribuie transportator din zonă. Lista poate fi afișată parțial pentru adoptatori (ex. „Transportatori disponibili: Brașov, Cluj, București, …”) sau folosită doar intern pentru organizarea transporturilor.

*Implementare:* câmpuri (da/nu sau listă de facilități) la nivel de membru sau de animal; afișare clară pe pagina animalului și/sau pe profilul adăpostului; când transportul e în altă zonă, ofertă/calcul preț + comision platformă; **model/listă Transportator** (zone naționale + internaționale). Filtre opționale după facilități (ex. „Arată doar animale cu transport disponibil”).

### Donații – loc separat pe pagină
- **Loc dedicat pe site** pentru:
  - **Donații în bani** – secțiune/pagină unde vizitatorii pot dona (link plată, IBAN, sau integrare plată online).
  - **Cei 3,5% din impozit** – informații și opțiune pentru redirectarea **3,5% din impozitul pe venit** (conform legislației din România) către platformă/asociație. Text explicativ + pași sau formular, ca lumea să știe cum să aloce cei 3,5%.
- Secțiunea e **separată** și vizibilă (ex. în meniu: „Sprijină” / „Donații” / „3,5%”) – nu amestecată cu restul conținutului.

### Limbi (multilingv)
- **Site-ul să aibă limbile frecvente** – selector de limbă în interfață; traduceri pentru texte, butoane, filtre, mesaje. Limbi de oferit: **română**, **engleză**, **spaniolă**, **italiană**, **germană**, **rusă**, eventual și altele (franceză, etc.). Româna rămâne limbă principală; celelalte pentru adoptatori din străinătate și diaspora.
- *Implementare:* i18n (internationalization) – fișiere de traduceri per limbă, prefix URL sau cookie pentru limbă selectată (ex. site.ro/en/, site.ro/ro/).

### Util pentru România
- **Tip animal (filtru)**: pe pagină **filtrare după tip** – **Câine**, **Pisică**, **Altele**. „Altele” = alte specii (păsări, magari, etc.) – unii utilizatori dau spre adopție și astfel de animale; modelul de date trebuie să permită tip „other” / listă extensibilă (ex. pasăre, magar, etc.).
- **Rasă / tip**: suport pentru **metis, maidanez** (nu doar rase pure) – filtre și etichete care au sens: „Metis”, „Maidanez”, eventual „Mix”, plus opțional rasa dacă se cunoaște.
- **Locație** – oraș/județ la animal sau la adăpost („Disponibil în Brașov”) – foarte util la filtre, mai ales la centralizare națională.
- **Adresă membru pe Google Maps** – la fiecare membru, **obligatoriu** adresa localizată pe Google Maps (detalii membru); afișare hartă pe profilul adăpostului/asociației.
- **Contact** – pe pagină: cum se aplică pentru adopție (telefon, e-mail, formular), ca să fie clar pentru adoptator.

### Calitate & încredere
- **Poze multiple** per animal (galerie), nu doar o imagine.
- **Status vizibil** – Adoptable / În procedură / Adoptat – actualizat din admin.
- **Data actualizării** – „Actualizat la …” pe anunț, ca lumea să știe că e proaspăt.
- **Date medicale obligatorii** – câmpuri obligatorii: sterilizat (da/nu), cipat (da/nu), microcipat (da/nu), vaccinuri / tratamente (conform politicii). Afișare clară pe pagina animalului.
- **Condiții adopție (adăposturi publice)** – adopția gratuită implică animal sterilizat, cipat, microcipat; site-ul afișează aceste informații și eventual validare (membrul bifează, admin poate verifica).
- **Validare imagini** – script/API care recunoaște animalul în poză; respingere sau revizie dacă imaginea nu conține animal (ex. avion, obiecte). Opțional: validare automată la upload.
- **Control postări per membru** – flux de verificare (manual sau semi-automat) înainte de publicare; raport sau listă de postări „în așteptare” pentru admin.

### Tehnic (infrastructură, nu verificare)
- **Performanță** – listă cu multe animale: paginare sau „încarcă mai multe”.
- **Mobile-friendly** – site-ul să arate bine pe telefon (mulți caută pe mobil).
- **Backup / export** – salvare date (animale) pentru siguranță.

---

## Note / concluzii din discuții

- **Problema de rezolvat**: promovare mai bună a animalelor – nu doar „un post pe Facebook”, ci un spațiu dedicat (site) unde anunțurile rămân, pot fi căutate/filtrate și partajate în timp.
- **Direcție**: site orientat spre adăposturi din România, cu focus pe vizibilitate și ușurință în folosire atât pentru cei care postează animalele, cât și pentru cei care caută să adopte.
- **„La grămadă”** = tot pachetul de verificare/control: tehnice, de imagine (validare poze), date medicale obligatorii, condiții adopție (sterilizat, cipat, microcipat). Un singur termen pentru toate astea când vorbim despre ele.
- **Clienți** = două categorii clare: (1) **adăposturi** din România – publice sau private; (2) **asociații de profil**. Ambele sunt membri care postează animale; adoptatorii sunt beneficiari, nu clienți plătitori.
- **Venituri**: pe lângă abonament (după 6 luni), **transport în altă zonă** (comision); **bandou de reclame** – producători de mâncare pentru animale, produse/servicii legate de animale – sursă de venit și conținut relevant pentru vizitatori.
- **Limbi**: site multilingv – **limbile frecvente** (română, engleză, spaniolă, italiană, germană, rusă, etc.); româna rămâne principală, celelalte pentru adoptatori din străinătate și diaspora.
- **Distribuire site:** obiectiv = **creșterea numărului de adopții** prin distribuire; va trebui o **listă a asociațiilor de profil din lume** (contact, țară) pentru outreach și parteneriate – tema e notată și la „Întrebări pentru ChatGPT” (unde/cum obținem lista).
- **Legal – juridice puternice:** **nu ne asumăm problemele** cu animalele adoptate (**nu putem controla animalul**); platforma e intermediar; **termeni și condiții puternici** (excludere răspundere, disclaimer), acceptare explicită (bifă), link în footer; formulare **validate de avocat**.
- **Persoane fizice** = încă **nedecis**; **e mai dificil cu ei**: nu au istoric/binitate, nu au transport/cazare, de obicei sunt cei care umplu Facebookul cu postări (câini pe câmp etc.). Tema e notată și la „Întrebări pentru ChatGPT” – e mai mult strategic/operațional.

---

## Prioritizare (sugestie)

| Prioritate | Ce |
|------------|-----|
| P0 (acum) | Filtre pe listă, link partajabil, site în română, contact clar; **juridice puternice** – termeni și condiții, disclaimer, excludere răspundere, acceptare explicită (bifă), validare avocat |
| P1 | Căutare, poze multiple, locație; **facilități pe pagină**; **loc pentru donații**; **limbi frecvente** (română, engleză, spaniolă, italiană, germană, rusă, etc.) – multilingv |
| P2 | **Membri** – cont per adăpost; **verificare foarte bună** (certificat înregistrare, copie buletin administrator, telefon, adresă, siguranță maximă); adresă Google Maps; date medicale; import bulk, raport simplu |
| P3 | **Control postări**; **validare imagini**; limită 50/lună + abonament; **listă transportatori**; **bandou reclame** (producători mâncare, produse animale); **concurs / laudă membru**; share, SEO, export |

*Poți schimba ordinea după ce e mai important pentru tine.*

---

## Distribuire site – creșterea numărului de adopții

- **Obiectiv:** **distribuirea site-ului** ca să **crească numărul de adopții** – site-ul să fie cunoscut și folosit de cât mai multe adăposturi, asociații și adoptatori.
- **Resursă necesară:** o **listă a asociațiilor de profil** (protecția animalelor, adopții) **din lume** – pentru outreach, parteneriate, invitare pe platformă și distribuire (România, Europa, SUA, etc.). Lista poate fi construită treptat (pe țări/regiuni), cu: nume asociație, țară, contact (site, e-mail), eventual domeniu (câini, pisici, animale în general). Folosire: trimitere invitații, parteneriate, schimb de linkuri, promovare comună.
- *Notă:* Pentru surse de astfel de liste (directoare internaționale, federății, ChatGPT) – vezi „Întrebări pentru ChatGPT”.

---

## Promovare / reclame și impingerea site-ului pe media (Google, Facebook, etc.)

**Întrebare:** Cât ar costa reclama și impingerea site-ului pe media (Google, Facebook, etc.)?

**Răspuns scurt:** Costul **depinde foarte mult** de țintă (România / străinătate), perioadă, tip campanie (căutare, display, social) și volum. Iată ordine de mărime și unde poți verifica cifre actuale.

- **Google Ads (căutare):**
  - CPC (cost per click) mediu global ~3–5 USD; în **Europa de Est / România** de obicei **mai mic** decât în Vest.
  - Buget lunar orientativ: de la **câteva sute RON** (testare) la **mii de RON** pentru campanii serioase. Poți seta un plafon zilnic (ex. 50–100 RON/zi) și ajusta.
- **Facebook / Instagram (Meta):**
  - CPC și CPM (cost per 1000 afișări) variază după țară și audiență. Europa de Est de obicei **mai ieftin** decât SUA/UK.
  - Buget lunar orientativ: similar – **sute–mii RON** în funcție de ambiție (ex. 500–2000 RON/lună pentru start, mai mult pentru acoperire mare).
- **Recomandări:**
  - Pentru **cifre actuale în România**: folosește **Google Ads Keyword Planner** (căutare) și **Facebook Ads Manager** (estimează reach și cost înainte de a plăti).
  - Pentru **plan de buget și strategie**: pune întrebarea în **ChatGPT** (sau un consultant media), ex. „Buget lunar pentru promovare site adopții animale România, Google + Facebook, 2025” – poate sugera alocare și pași.
- **Notă:** Primele 6 luni site-ul e gratuit pentru membri; poți aloca o parte din buget la promovare (reclame) ca să atragi atât adoptatori, cât și adăposturi pe platformă.

---

## Întrebări / teme pentru ChatGPT (sau discuție separată)

*Teme mai mult strategice, operaționale sau de business – nu neapărat de cod. Poți copia în ChatGPT sau într-un alt chat ca să le dezvolți.*

- **Cum ne comportăm cu persoanele fizice?** Nu au istoric sau binitate, nu au transport/cazare, de obicei sunt unii care umplu Facebookul cu postări (câini pe câmp, etc.). Vrem să găsim o metodă să le integrăm (sau să decidem că nu le permitem / doar prin partener). Cum definim reguli, limite, verificări pentru persoane fizice vs. adăposturi/asociații?
- **Buget exact pentru reclame (Google, Facebook) în România 2025?** Pentru plan de media și cifre actuale (CPC, CPM, buget lunar recomandat pentru site adopții) – folosește ChatGPT sau Google Keyword Planner / Facebook Ads Manager.
- **Listă asociații de profil din lume:** De unde sau cum obțin / construiesc o **listă a asociațiilor de profil** (protecția animalelor, adopții) **din întreaga lume** (pe țări/regiuni) – cu contact (site, e-mail) – pentru parteneriate și distribuirea site-ului? Există directoare, federății, baze de date? Cum o structurază pe țări și domenii?
- **Formulare legală disclaimer / termeni:** Cerință: platforma nu răspunde pentru problemele cu animalele adoptate (nu putem controla animalul). Un avocat poate redacta clauzele exacte; ChatGPT poate sugera formulări de bază pentru „terms of use” și „limitation of liability” pentru platformă de adopții (apoi validare avocat).

*Adaugă aici alte întrebări care ți se par „diferite” de ce face Cursor (cod) – pentru ChatGPT sau discuție separată.*

---

*Ultima actualizare: feb 2025*
