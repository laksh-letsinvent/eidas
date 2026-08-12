// Ported verbatim from the standalone prototype
// (portal/content/walkthrough/source.html, provenance copy). Story bodies
// are HTML strings produced by pure functions, deliberately not rewritten
// as React components (BUILD_PROMPT_PHASE7-9.md "take the shortcut").
// The interactive selective-disclosure step is the one exception — it is
// reimplemented as a real React component in SelectiveDisclosureLab.tsx.

export interface Nav {
  label: string;
  next: string;
}

export interface Expl {
  t: string;
  b: string;
}

export interface Step {
  app: string;
  icon: string;
  right?: string;
  body: string;
  mount?: "sd";
  progress?: "qes";
  auto?: number;
  primary?: Nav;
  secondary?: Nav;
  expl: Expl;
  tech?: string;
  fact?: string;
}

export interface Story {
  id: string;
  icon: string;
  title: string;
  tag: string;
  blurb: string;
  steps: Step[];
}

export interface BandEntry {
  iss?: string;
  issIcon?: string;
  issRole?: string;
  issDesc?: string;
  ver?: string;
  verIcon?: string;
  verRole?: string;
  verDesc?: string;
  verBad?: boolean;
  flow?: "iss>you" | "you>iss" | "ver>you" | "you>ver";
  label?: string;
  cap: string;
}

export interface PidClaim {
  k: string;
  v: string;
  lbl: string;
}

const ok = (label: string, next: string): Nav => ({ label, next });

function heroBlock(em: string, grad?: string): string {
  return `<div class="hero" ${grad ? `style="background:${grad}"` : ""}><div class="glow"></div><div class="em">${em}</div></div>`;
}
function okBlock(txt: string): string {
  return `<div class="okwrap"><div class="okcircle"><svg viewBox="0 0 50 50"><path d="M12 26 L21 35 L38 16"/></svg></div></div>
          <div class="h1p" style="text-align:center">${txt}</div>`;
}
function credCard(cls: string, type: string, name: string, info: string, em: string, badge?: string): string {
  return `<div class="cred ${cls}">
    <div class="ct">${type}</div><div class="cn">${name}</div><div class="ci">${info}</div>
    ${badge ? `<div class="badge">✓ ${badge}</div>` : ""}<div class="bigem">${em}</div></div>`;
}
function verifier(icon: string, name: string, who: string, trusted = true, note = ""): string {
  return `<div class="reqcard"><div class="reqhead">
    <div class="lg2">${icon}</div>
    <div><div style="font-size:14px;font-weight:650">${name}</div>
    <div style="font-size:11px;color:var(--muted);margin-top:2px">${who}</div>
    <div class="trust ${trusted ? "" : "bad"}">${trusted ? "✓ Registered verifier · checked just now" : "⚠ Not in the EU trust register"}</div></div>
  </div>${note ? `<div style="font-size:11.5px;color:#aab4c9;margin-top:11px;line-height:1.5">${note}</div>` : ""}</div>`;
}
interface FieldSpec {
  k: string;
  v: string;
  off?: boolean;
  opt?: boolean;
}
function fields(list: FieldSpec[]): string {
  return list
    .map(
      (f, i) => `<div class="field ${f.off ? "off" : ""}" data-i="${i}" ${f.opt ? 'data-opt="1"' : ""}>
      <div><div class="fk">${f.k}</div><div class="fv">${f.v}</div></div>
      ${f.opt ? '<div class="sw"></div>' : '<div class="lock">required</div>'}
    </div>`
    )
    .join("");
}
function withheld(list: string[]): string {
  return `<div class="notshared"><div style="font-size:10px;text-transform:uppercase;letter-spacing:1.1px;color:var(--muted);margin-bottom:7px">Stays in your wallet</div>
    ${list.map((x) => `<div class="ns-item"><span class="x">✕</span>${x}</div>`).join("")}</div>`;
}
function compare(oldV: string, oldL: string, newV: string, newL: string): string {
  return `<div class="rowsplit" style="margin-top:14px">
    <div class="old"><div class="big">${oldV}</div><div class="lbl">${oldL}</div></div>
    <div class="new"><div class="big">${newV}</div><div class="lbl">${newL}</div></div></div>`;
}
function scanScreen(title: string, sub: string): string {
  return `<div class="bio"><div class="ring">
      <svg viewBox="0 0 120 120"><circle cx="60" cy="60" r="54" stroke="#1f2940" stroke-width="5" fill="none"/>
      <circle cx="60" cy="60" r="54" stroke="var(--eu2)" stroke-width="5" fill="none" stroke-linecap="round"
       stroke-dasharray="339" stroke-dashoffset="90" style="animation:spin 1.4s linear infinite;transform-origin:center"/></svg>
      <div class="em2">${title}</div><div class="scanline"></div></div></div>
      <div class="pp" style="text-align:center;margin-top:14px">${sub}</div>`;
}

function fnv(s: string): string {
  let x = 0x811c9dc5;
  for (let i = 0; i < s.length; i++) {
    x ^= s.charCodeAt(i);
    x = Math.imul(x, 0x01000193) >>> 0;
  }
  return x.toString(16).padStart(8, "0");
}
export function claimHash(k: string, v: string): string {
  return fnv(k + "|" + v + "|salt") + fnv(v + k);
}

export const PID_CLAIMS: PidClaim[] = [
  { k: "family_name", v: "Singhal", lbl: "Family name" },
  { k: "given_name", v: "Laksh", lbl: "Given name" },
  { k: "birth_date", v: "1985-03-14", lbl: "Date of birth" },
  { k: "age_over_18", v: "true", lbl: "Over 18" },
  { k: "age_over_21", v: "true", lbl: "Over 21" },
  { k: "age_in_years", v: "41", lbl: "Age in years" },
  { k: "nationality", v: "GB", lbl: "Nationality" },
  { k: "resident_address", v: "42 Sandringham Rd, London E8", lbl: "Address" },
  { k: "birth_place", v: "Saharanpur, India", lbl: "Place of birth" },
  { k: "document_number", v: "561234789", lbl: "Document number" },
];
export const PID_FIXED: PidClaim[] = [
  { k: "iss", v: "HM Passport Office", lbl: "Who issued it" },
  { k: "exp", v: "2034-03-14", lbl: "Expires" },
  { k: "cnf", v: "your wallet key", lbl: "Bound to" },
];
export const SD_PRESETS: Record<string, string[]> = {
  bank: ["family_name", "given_name", "birth_date", "nationality", "resident_address"],
  age: ["age_over_18"],
  parcel: ["family_name", "resident_address"],
  none: [],
};

export const STORIES: Story[] = [
{
  id:'setup', icon:'🪪', title:'Get your wallet', tag:'Once, then never again',
  blurb:'Prove who you are one time. Carry it everywhere after that.',
  steps:[
    {
      app:'EU Digital Identity Wallet', icon:'🇪🇺', right:'Setup',
      body: heroBlock('👛') + `<div class="h1p">One identity. Every service. Across 27 countries.</div>
        <div class="pp">Your government issues you a digital version of who you are. It lives on your phone, not on a company server. You decide what leaves it, every single time.</div>
        <div class="spacer"></div>
        <span class="pill">🔒 Stored on your device</span><span class="pill">🇪🇺 Works EU-wide</span><span class="pill">🚫 No tracking by design</span>`,
      primary: ok('Set up my wallet','next'),
      expl:{t:'A wallet, not an account',b:'The wallet is an app you control. There is no central database of your logins — the issuer who gave you a credential does not see where you use it. That property, called unlinkability, is the whole reason this is different from "Sign in with a big tech company".'},
      tech:`App is certified against the <em>ARF</em> (Architecture &amp; Reference Framework).\nKey material sits in a <em>WSCD</em> — secure element / eUICC / HSM-backed remote.\nTarget assurance: <em>LoA High</em> per eIDAS Art. 8.`,
      fact:`<div class="kv"><b>Legal basis</b><span>Regulation (EU) 2024/1183 — eIDAS 2.0</span></div>
            <div class="kv"><b>Member state duty</b><span>Offer at least one wallet to every citizen</span></div>
            <div class="kv"><b>Cost to user</b><span>Free, and use is voluntary</span></div>`
    },
    {
      app:'EU Digital Identity Wallet', icon:'🇪🇺', right:'Step 1 of 3',
      body:`<div class="steps"><i class="done"></i><i></i><i></i></div>
        <div class="h1p">Hold your passport to the back of your phone</div>
        <div class="pp">The chip inside proves the document is real and unaltered. No typing. No uploading a blurry photo.</div>
        ${scanScreen('🛂','Reading the chip…')}`,
      auto:2400, primary: ok('Continue','next'),
      expl:{t:'Why the chip matters',b:'A photo of a passport can be edited. The chip is signed by the issuing country and cannot be forged. Reading it over NFC moves document verification from "does this image look right" to cryptographic proof — which is why fraud rates on NFC journeys are a fraction of photo-only ones.'},
      tech:`NFC read of <em>ICAO 9303</em> LDS. Passive authentication verifies\nthe <em>SOD</em> signature against the country signing certificate (CSCA).\nChip Authentication defeats cloning.`,
      fact:`<div class="kv"><b>What is read</b><span>Name, DOB, document number, photo, expiry</span></div>
            <div class="kv"><b>What is proven</b><span>The document is genuine and unmodified</span></div>`
    },
    {
      app:'EU Digital Identity Wallet', icon:'🇪🇺', right:'Step 2 of 3',
      body:`<div class="steps"><i class="done"></i><i class="done"></i><i></i></div>
        <div class="h1p">Now show us it's really you</div>
        <div class="pp">Turn your head slowly. This checks a live person is holding the passport — not a photo, a mask, or a deepfake.</div>
        ${scanScreen('🙂','Liveness check in progress…')}
        <div class="infobox" style="margin-top:14px">Your face scan is compared to the passport photo, then deleted. It is not kept as a biometric record by the wallet.</div>`,
      auto:2600, primary: ok('Continue','next'),
      expl:{t:'Binding the document to the human',b:'Two separate questions get answered here. Is the document real? Is the person presenting it the person in the document? Most identity fraud in banking exploits the gap between those two — a genuine document held by someone else.'},
      tech:`Face match against chip DG2 image + <em>presentation attack detection</em>\n(ISO/IEC 30107-3, Level 2). Injection-attack detection on the camera stream.`,
      fact:`<div class="kv"><b>Deepfake pressure</b><span>Injection attacks now outpace printed-mask attacks</span></div>
            <div class="kv"><b>Retention</b><span>Template discarded after match in this design</span></div>`
    },
    {
      app:'EU Digital Identity Wallet', icon:'🇪🇺', right:'Step 3 of 3',
      body:`<div class="steps"><i class="done"></i><i class="done"></i><i class="done"></i></div>`+
        okBlock('Your PID has been issued')+
        `<div class="pp" style="text-align:center;margin-bottom:15px">PID stands for <b style="color:#e8edf7">Person Identification Data</b>. It is the one credential your government issues directly, and the root that everything else hangs off.</div>
        ${credCard('gov','Person Identification Data — PID','Laksh Singhal','Issued by HM Passport Office · valid to 2034','🛂','Government · LoA High')}
        <div style="font-size:9.5px;text-transform:uppercase;letter-spacing:1.1px;color:var(--muted);margin:16px 0 8px">Inside it — always present</div>
        ${[['Family name','Singhal'],['Given name','Laksh'],['Date of birth','14 March 1985'],['Unique identifier','GB-PID-7749-2213'],['Issuing country &amp; authority','GB · HM Passport Office']]
          .map(r=>`<div class="field"><div><div class="fk">${r[0]}</div><div class="fv">${r[1]}</div></div><div class="lock">mandatory</div></div>`).join('')}
        <div style="font-size:9.5px;text-transform:uppercase;letter-spacing:1.1px;color:var(--muted);margin:14px 0 8px">Inside it — your member state may add</div>
        ${[['Address','42 Sandringham Rd, London E8'],['Nationality','United Kingdom'],['Over 18','true'],['Place of birth','Saharanpur, India'],['Portrait','Photo from your passport chip']]
          .map(r=>`<div class="field"><div><div class="fk">${r[0]}</div><div class="fv">${r[1]}</div></div><div class="lock">optional</div></div>`).join('')}
        <div class="infobox" style="margin-top:14px">You hold <b style="color:#e8edf7">one PID</b>, from one member state. You can hold any number of other credentials — and every one of them will be issued to you by first checking this PID.</div>`,
      primary: ok('So how do I get a driving licence? →','story:issue'),
      secondary: ok('See my full wallet','next'),
      expl:{t:'PID is the root of trust, not just another card',b:'Everything else in the wallet is downstream of PID. When DVLA, your bank or your university issues you something, they identify you by asking for PID attributes first. That is why the assurance level of PID matters so much — weaken it and every credential derived from it inherits the weakness. It is also why PID must come from the state: no private provider can assert legal identity.'},
      tech:`PID issued per the <em>PID Rulebook</em> in the ARF. Mandatory attributes:\nfamily_name, given_name, birth_date, issuance/expiry, issuing authority\n+ a unique identifier. Optional set includes address, nationality,\n<em>age_over_18</em>, portrait, birth_place, age_in_years.\nFormat: <em>SD-JWT VC</em> or <em>ISO mdoc</em>. Assurance: <em>LoA High</em>.`,
      fact:`<div class="kv"><b>PID</b><span>Person Identification Data — issued by the state, one per wallet</span></div>
            <div class="kv"><b>QEAA</b><span>Qualified Electronic Attestation of Attributes — from a QTSP</span></div>
            <div class="kv"><b>PuB-EAA</b><span>Attestation from a public body, e.g. DVLA</span></div>
            <div class="kv"><b>EAA</b><span>Ordinary attestation, e.g. a loyalty tier. Anyone may issue.</span></div>`
    },
    {
      app:'EU Digital Identity Wallet', icon:'🇪🇺', right:'My wallet',
      body:`<div class="h1p">Your wallet, a year later</div>
        <div class="pp" style="margin-bottom:15px">PID sits at the root. Everything below it was issued by whoever is actually authoritative for that fact — and each one was issued by first checking your PID.</div>
        ${credCard('gov','Person Identification Data — PID','Laksh Singhal','HM Passport Office · the root credential','🛂','Government')}
        <div style="text-align:center;color:#3d4b6b;font-size:15px;margin:2px 0 6px">↓ each of these asked for your PID first ↓</div>
        ${credCard('dl','Mobile Driving Licence — PuB-EAA','Categories B, BE','Issued by DVLA · valid to 2031','🚗','DVLA')}
        ${credCard('bank','Bank account attestation — EAA','Lara Bank · GB••••4417','Issued by Lara Bank · refreshed daily','🏦','Lara Bank')}
        ${credCard('edu','Degree certificate — EAA','MSc Computer Science','Issued by University of Warwick','🎓','University')}
        ${credCard('health','European Health Insurance — PuB-EAA','EHIC · UK','Issued by NHS Business Services','⚕️','NHS')}`,
      primary: ok('Watch a licence get issued →','story:issue'),
      secondary: ok('Skip to using it','story:bank'),
      expl:{t:'Credentials come from source',b:'Each attestation is signed by the party that actually knows the fact. Your university signs your degree. Your bank signs that you hold an account. Nobody has to phone anyone to check — the signature is the check. This is what kills the "upload a PDF and wait three days" pattern, and it is why the wallet is an ecosystem play rather than a single product.'},
      tech:`Credentials as <em>SD-JWT VC</em> (selectively disclosable) and <em>ISO 18013-5 mdoc</em>.\nIssued over <em>OpenID4VCI</em>. Revocation via <em>Token Status List</em>.`,
      fact:`<div class="kv"><b>Issuer variety</b><span>State, public bodies, QTSPs and ordinary companies can all issue</span></div>
            <div class="kv"><b>Trust differs</b><span>A QEAA carries legal presumption; an EAA does not</span></div>`
    }
  ]
},

{
  id:'issue', icon:'🚗', title:'Get a driving licence issued', tag:'One org, two roles',
  blurb:'Watch DVLA act as a verifier, then switch to being an issuer.',
  steps:[
    {
      app:'DVLA', icon:'🚗', right:'Add to wallet',
      body: heroBlock('🚗','linear-gradient(135deg,#3d2a5f,#1d1733)') +
        `<div class="h1p">Add your driving licence to your wallet</div>
        <div class="pp">DVLA already holds your record. But it cannot just push a credential to a phone — it has to be certain the phone belongs to you first.</div>
        <div class="spacer"></div>
        <div class="infobox">So before DVLA can issue you anything, it has to <b style="color:#e8edf7">verify</b> you. Watch the band above: DVLA is about to light up on the <b style="color:#e8edf7">right</b>, as a verifier.</div>`,
      primary: ok('Start','next'),
      expl:{t:'Issuance always begins with verification',b:'This is the step almost every explainer skips, and it is the one that makes the model click. Nobody can issue you a credential without first identifying you, so every issuer is briefly a verifier. Roles belong to the moment, not to the organisation — DVLA is a verifier for the next twenty seconds and an issuer for the twenty after that.'},
      tech:`<em>OpenID4VCI</em> issuance, with an <em>OpenID4VP</em> presentation\nrequest embedded as the authorisation step. The credential offer\nis only fulfilled once the PID presentation validates.`,
      fact:`<div class="kv"><b>Pattern name</b><span>PID-based issuance — derive new credentials from the root</span></div>`
    },
    {
      app:'EU Digital Identity Wallet', icon:'🇪🇺', right:'Request',
      body:`<div class="h1p" style="font-size:18px">DVLA needs to find your record</div>
        ${verifier('🚗','DVLA','Driver &amp; Vehicle Licensing Agency · public body',true,'Right now DVLA is acting as a <b>verifier</b>. It is asking your wallet to prove who you are, using the PID your government already issued.')}
        ${fields([
          {k:'Family name',v:'Singhal'},
          {k:'Given name',v:'Laksh'},
          {k:'Date of birth',v:'14 March 1985'},
          {k:'Address',v:'42 Sandringham Rd, London E8'}
        ])}
        ${withheld(['Your unique PID identifier','Your place of birth','Your nationality','Your passport number','Every other credential in your wallet'])}
        <div class="infobox" style="margin-top:12px">Four attributes is all DVLA needs to match you to an existing driver record. It does not need your passport number — it already has its own.</div>`,
      primary: ok('Share with DVLA','next'),
      secondary: ok('Cancel','back'),
      expl:{t:'The same request pattern as the bank',b:'Compare this screen to the Lara Bank one. Identical mechanics: a registered relying party asks for named PID attributes, you approve, a signed response goes back. Once you see that issuance and verification share one plumbing layer, the architecture stops looking like a pile of special cases.'},
      tech:`Presentation request over <em>OpenID4VP</em>, scoped to PID claims.\nDVLA validates the Home Office signature and the key-binding proof,\nthen matches against its own driver database.`,
      fact:`<div class="kv"><b>Matching</b><span>Name + DOB + address is the classic record-match tuple</span></div>`
    },
    {
      app:'DVLA', icon:'🚗', right:'Record found',
      body: okBlock('Record matched') +
        `<div class="pp" style="text-align:center;margin-bottom:14px">Licence SINGH851014LS9AB · Categories B, BE · Valid to 12 Nov 2031 · No endorsements</div>
        <div class="okbox">Now the roles swap. DVLA has finished verifying you and is about to <b>issue</b> you a credential. Look at the band above — DVLA has moved from the right-hand node to the left.</div>
        <div class="spacer"></div>
        <div class="pp sm">Your licence will be cryptographically bound to this phone. A copy on another device will not verify, because the key it is bound to lives only here.</div>`,
      primary: ok('Issue my licence','next'),
      expl:{t:'The role switch is the lesson',b:'One organisation, two roles, thirty seconds apart. This is why "issuer" and "verifier" are the wrong things to put on an org chart and the right things to put on a sequence step. A bank is a verifier at onboarding and an issuer when it attests you hold an account — sometimes in the same session.'},
      tech:`Credential offer issued; wallet performs the <em>OpenID4VCI</em>\ntoken exchange. Wallet generates a fresh key pair; the public key\ngoes into the credential as <em>cnf</em>, binding it to this device.`,
      fact:`<div class="kv"><b>Holder binding</b><span>Credential is useless without the private key on your device</span></div>
            <div class="kv"><b>Why it matters</b><span>Stops a stolen credential being replayed from another phone</span></div>`
    },
    {
      app:'EU Digital Identity Wallet', icon:'🇪🇺', right:'Issued',
      body: okBlock('Licence added') +
        credCard('dl','Mobile Driving Licence','Categories B, BE','Issued by DVLA · valid to 12 Nov 2031','🚗','DVLA · PuB-EAA') +
        `<div style="font-size:9.5px;text-transform:uppercase;letter-spacing:1.1px;color:var(--muted);margin:16px 0 8px">What DVLA put inside it</div>
        ${[['driving_privileges','B, BE'],['expiry_date','2031-11-12'],['issue_date','2021-11-13'],['document_number','SINGH851014LS9AB'],['portrait','Photo on file'],['age_over_18','true'],['age_over_21','true'],['endorsements','none']]
          .map(r=>`<div class="field"><div><div class="fk mono" style="font-size:10px">${r[0]}</div><div class="fv">${r[1]}</div></div></div>`).join('')}
        <div class="infobox" style="margin-top:13px">Notice DVLA included <b style="color:#e8edf7">age_over_18</b> and <b style="color:#e8edf7">age_over_21</b> as their own separate claims. That is a deliberate design choice at issuance time — it is what lets you later prove your age from a licence without revealing your birthday. Selective disclosure has to be built in when the credential is made. You cannot add it afterwards.</div>`,
      primary: ok('Show me how that works →','story:disclose'),
      secondary: ok('Continue','next'),
      expl:{t:'Privacy is decided at issuance, not at presentation',b:'The most consequential design decision in this whole architecture happens here, in a schema nobody sees. If DVLA had stored only birth_date, every age check would leak your birthday forever, no matter how good the wallet UX became. Issuers who ship lazy schemas permanently cap how private their credential can ever be — and this is the thing a bank issuing account attestations should get right on day one.'},
      tech:`Claims salted and hashed individually at issuance (<em>SD-JWT</em>)\nor as separate mdoc data elements. Derived claims like\n<em>age_over_NN</em> must be minted by the issuer — the wallet\ncannot compute them and keep the issuer signature valid.`,
      fact:`<div class="kv"><b>Design rule</b><span>Mint every predicate a verifier might plausibly need</span></div>
            <div class="kv"><b>Failure mode</b><span>Storing only raw values forces over-disclosure forever</span></div>`
    },
    {
      app:'EU Digital Identity Wallet', icon:'🇪🇺', right:'Revocation',
      body:`<div class="h1p" style="font-size:19px">And if you lose your licence?</div>
        <div class="pp">A court disqualifies you. Under the plastic regime, someone has to physically take the card off you — and until they do, it still looks valid to every barman and rental desk in Europe.</div>
        <div class="spacer"></div>
        <div class="field" style="border-color:#ff5f6d40;background:#ff5f6d0f"><div><div class="fk">Status list position 4,417</div><div class="fv" style="color:var(--bad)">REVOKED · 12 Aug 2026</div></div></div>
        <div class="spacer"></div>
        <div class="okbox">DVLA flips one bit in a public status list. The next verifier to check sees a revoked credential — instantly, everywhere, without DVLA being told who asked or where.</div>
        <div class="spacer"></div>
        <div class="infobox">The honest caveat: status checking needs the verifier to be online, or to have a recent copy of the list. Fully offline verification means accepting a staleness window, and that window is a risk decision — not a technical detail to wave away.</div>`,
      primary: ok('Next: how disclosure works →','story:disclose'),
      expl:{t:'Revocation is where paper credentials fail worst',b:'A physical licence stays convincing long after it stops being valid. A status list closes that gap to minutes. But it introduces a genuine trade-off that IDV teams underplay: online status checks give freshness and cost you offline capability, while cached lists preserve offline use and give you a staleness window. Pick per journey — a bar door can tolerate 24-hour staleness, a car hire desk probably cannot.'},
      tech:`<em>Token Status List</em> (IETF): a compressed bitstring published\nby the issuer. Verifier fetches the list, not the credential —\nso the issuer never learns which credential was checked.`,
      fact:`<div class="kv"><b>Privacy property</b><span>Issuer sees list downloads, not individual lookups</span></div>
            <div class="kv"><b>Trade-off</b><span>Freshness vs offline capability. Choose per journey.</span></div>`
    }
  ]
},

{
  id:'bank', icon:'🏦', title:'Open a bank account', tag:'11 minutes → 40 seconds',
  blurb:'The KYC journey everyone abandons, without the abandoning.',
  steps:[
    {
      app:'Lara Bank', icon:'🏦', right:'New account',
      body: heroBlock('🏦','linear-gradient(135deg,#0f4038,#0e2129)') +
        `<div class="h1p">Open your Lara Bank current account</div>
        <div class="pp">We're legally required to know who you are before we can open an account. You can prove it in one tap instead of twenty.</div>
        <div class="spacer"></div>
        <div class="infobox">The old way: photograph your passport, take a selfie, type your address, wait for a manual review, sometimes post a utility bill. Roughly <b style="color:#e8edf7">1 in 4 people give up</b> somewhere in that.</div>`,
      primary: ok('Continue with EU Wallet','next'),
      secondary: ok('Do it the old way','next2'),
      expl:{t:'Onboarding drop-off is the real cost',b:'Banks obsess over fraud losses and undercount abandonment. A 25% drop-off on 50,000 monthly applicants is 12,500 people who wanted to be customers and are now someone else\'s. Wallet-based KYC attacks that number directly, which is why the business case rarely rests on fraud alone.'},
      tech:`Relying party initiates <em>OpenID4VP</em> presentation request.\nRP must be registered and hold an <em>access certificate</em> stating\nwhich attributes it is entitled to ask for.`,
      fact:`<div class="kv"><b>Obligation</b><span>Under eIDAS 2.0, banks must accept the wallet where strong user ID is required</span></div>
            <div class="kv"><b>Deadline</b><span>Wallets available from 2026; private-sector acceptance follows</span></div>`
    },
    {
      app:'EU Digital Identity Wallet', icon:'🇪🇺', right:'Request',
      body:`<div class="h1p" style="font-size:18px">Lara Bank is asking for your details</div>
        ${verifier('🏦','Lara Bank plc','Company no. 09842217 · FCA authorised',true,'They asked for what a bank legally needs to open an account — and their registration says they are allowed to ask for it.')}
        ${fields([
          {k:'Full name',v:'Laksh Singhal'},
          {k:'Date of birth',v:'14 March 1985'},
          {k:'Nationality',v:'United Kingdom'},
          {k:'Current address',v:'42 Sandringham Rd, London E8'},
          {k:'Mobile number',v:'+44 7•• ••• 4412', opt:true}
        ])}
        ${withheld(['Passport number','Your photo','Driving licence','Any other account you hold','Where else you used your wallet'])}`,
      primary: ok('Share and continue','next'),
      secondary: ok('Cancel','back'),
      expl:{t:'The bank sees exactly this, and only this',b:'Notice what did not travel: the passport number, the document image, the photo. The bank gets government-verified attributes rather than a document it has to interpret. Its evidence quality goes up while the data it holds — and has to protect, and may have to breach-notify on — goes down.'},
      tech:`Presentation Definition requests specific claims:\n<em>given_name, family_name, birth_date, nationality, resident_address</em>\nWallet returns an <em>SD-JWT</em> disclosing only those, plus a\nkey-binding JWT proving possession. Bank verifies issuer signature offline.`,
      fact:`<div class="kv"><b>GDPR link</b><span>Data minimisation (Art. 5) becomes technically enforced, not just promised</span></div>
            <div class="kv"><b>Breach exposure</b><span>Data you never collected cannot leak</span></div>`
    },
    {
      app:'EU Digital Identity Wallet', icon:'🇪🇺', right:'Confirm',
      body:`<div class="h1p" style="text-align:center;font-size:19px">Confirm it's you</div>
        ${scanScreen('👤','Face ID')}
        <div class="pp sm" style="text-align:center;margin-top:12px">Nothing is sent until you approve. The wallet cannot share on your behalf.</div>`,
      auto:1900, primary: ok('Approved','next'),
      expl:{t:'User presence is mandatory, not optional',b:'Every disclosure requires an explicit act by the holder. This is what stops malware or a rogue app silently draining your credentials, and it is the same control that makes the wallet usable as a signing device later.'},
      tech:`User authentication unlocks the private key in the <em>WSCD</em>.\nSigns the <em>key-binding JWT</em> over the verifier nonce + audience —\nproving this wallet holds the credential and the response is fresh.`,
      fact:`<div class="kv"><b>Replay defence</b><span>Verifier nonce means a captured response is useless</span></div>`
    },
    {
      app:'Lara Bank', icon:'🏦', right:'Done',
      body: okBlock('Account open') +
        `<div class="pp" style="text-align:center">Sort code 04-29-11 · Account ••••4417<br>Your card is on its way.</div>
        ${compare('11 min','Typical KYC journey','40 sec','With your wallet')}
        ${compare('~24%','Applicants who drop off','~4%','Drop-off with wallet')}
        <div class="okbox" style="margin-top:14px">The bank also received a signed, auditable record of exactly what it was given and when — which is precisely what a regulator asks for during a file review.</div>
        <div class="legalnote" style="margin-top:10px">Figures illustrative. Lara Bank is a fictional case study.</div>`,
      primary: ok('Next story: prove your age →','story:age'),
      expl:{t:'Compliance got easier, not harder',b:'The usual framing is that KYC rules fight good UX. Here the regulated outcome and the fast outcome are the same path. The bank\'s evidence is stronger (government-signed attributes, cryptographic freshness) and the customer\'s journey is shorter. When compliance and conversion point the same way, adoption stops being an argument.'},
      tech:`Bank stores: disclosed claims, issuer signature, nonce, timestamp,\ntrust-chain state at time of verification. That bundle is the KYC record.`,
      fact:`<div class="kv"><b>Re-KYC</b><span>Refresh becomes a re-presentation, not a new document collection</span></div>
            <div class="kv"><b>AMLR 2027</b><span>EU rules push toward verified, reusable identity evidence</span></div>`
    }
  ]
},

{
  id:'age', icon:'🍷', title:'Prove you are over 18', tag:'The magic trick',
  blurb:'Answer the question without revealing the answer.',
  steps:[
    {
      app:'Vintners Direct', icon:'🍷', right:'Checkout',
      body: heroBlock('🍷','linear-gradient(135deg,#5c1b32,#2a0f1c)') +
        `<div class="h1p">Age check required</div>
        <div class="pp">You're buying a case of Barolo. The retailer must confirm you're over 18.</div>
        <div class="spacer"></div>
        <div class="infobox">Today they'd photograph your driving licence — which also tells them your exact birthday, your full address, your licence number and what you look like. To answer a yes/no question.</div>`,
      primary: ok('Verify with wallet','next'),
      expl:{t:'Over-collection is the norm',b:'Every age check today hands over an entire identity document to answer a single boolean. That data then sits on a retailer\'s server, gets breached, and turns into account-takeover material. The mismatch between the question asked and the data handed over is the single clearest failure of the current system.'},
      tech:`Retailer requests the <em>age_over_18</em> attribute rather than <em>birth_date</em>.`,
      fact:`<div class="kv"><b>UK angle</b><span>Online Safety Act age assurance creates the same demand outside the EU</span></div>`
    },
    {
      app:'EU Digital Identity Wallet', icon:'🇪🇺', right:'Request',
      body:`<div class="h1p" style="font-size:18px">One question. One answer.</div>
        ${verifier('🍷','Vintners Direct Ltd','Licensed alcohol retailer',true,'')}
        <div class="field"><div><div class="fk">The only thing they receive</div><div class="fv" style="font-size:17px;color:var(--ok)">Over 18 &nbsp;✓</div></div><div class="lock">required</div></div>
        ${withheld(['Your date of birth','Your name','Your address','Your photo','Your licence number','Your exact age'])}
        <div class="okbox" style="margin-top:14px">They learn <b>true</b>. They do not learn <b>how true</b>. Your birthday stays yours.</div>`,
      primary: ok('Share "Over 18"','next'),
      secondary: ok('Cancel','back'),
      expl:{t:'Selective disclosure, in one screen',b:'This is the part people find hard to believe. The credential contains your date of birth, but the wallet can reveal a derived claim — over 18 — while the retailer still verifies the government signature behind it. Proof without exposure. If you only remember one thing about the EUDI Wallet, make it this screen.'},
      tech:`<em>SD-JWT</em>: each claim is salted and hashed at issuance.\nThe holder discloses only the salt+value pairs it chooses;\nthe issuer signature still verifies over the whole set.\nISO mdoc equivalent: <em>age_over_NN</em> data elements.\nZKP variants push this further — proof with no correlatable identifier.`,
      fact:`<div class="kv"><b>Name for it</b><span>Selective disclosure / predicate proof</span></div>
            <div class="kv"><b>Why it's hard</b><span>Needs issuer support at issuance time — you cannot bolt it on later</span></div>`
    },
    {
      app:'Vintners Direct', icon:'🍷', right:'Confirmed',
      body: okBlock('Age confirmed') +
        `<div class="pp" style="text-align:center">Order placed. Delivery Thursday.</div>
        ${compare('6 fields','Old way: data given away','1 fact','Wallet: data given away')}
        <div class="infobox" style="margin-top:14px">The retailer keeps a signed proof that a valid age check happened — enough to satisfy their licensing regulator — without keeping anything that identifies you.</div>`,
      primary: ok('But how does that work? →','story:disclose'),
      secondary: ok('Skip ahead','story:phish'),
      expl:{t:'Both sides win, which is rare',b:'The retailer wanted evidence for its licence, not your birthday — it was collecting the birthday because that was the only option available. Give it a better option and the over-collection disappears without anyone having to be persuaded to care about privacy.'},
      tech:`Retailer retains: signed presentation, timestamp, issuer trust chain.\nNo PII. Audit-satisfying, breach-irrelevant.`,
      fact:`<div class="kv"><b>Same pattern</b><span>Over 65 for concessions, resident of X for local services, income band for benefits</span></div>`
    }
  ]
},

{
  id:'disclose', icon:'🔬', title:'How selective disclosure works', tag:'Interactive',
  blurb:'Open the credential up and choose, claim by claim, what leaves.',
  steps:[
    {
      app:'EU Digital Identity Wallet', icon:'🇪🇺', right:'Inside the PID',
      body:`<div class="h1p" style="font-size:19px">What the Home Office actually signed</div>
        <div class="pp" style="margin-bottom:14px">Your PID is not one blob of data. At issuance, every claim was given a random salt and hashed separately. The signature covers <b style="color:#e8edf7">the list of hashes</b> — not the values.</div>
        ${PID_CLAIMS.map(c=>`<div class="sdrow fixed" style="opacity:1">
            <div><div class="ck mono">${c.k}</div><div class="cv">${c.v}</div></div>
            <div class="ch mono">↳ ${claimHash(c.k,c.v).slice(0,12)}…</div>
          </div>`).join('')}
        <div class="okbox" style="margin-top:14px">One signature over ten independent hashes. That single design choice is what makes everything else possible — you can hand over any subset and the signature still verifies over the whole set.</div>`,
      primary: ok('Now you choose →','next'),
      expl:{t:'One signature, ten separable facts',b:'A normal signed document is all-or-nothing: alter one byte and the signature breaks, so you must reveal everything to prove anything. Salting and hashing each claim separately breaks that coupling. The issuer commits to ten facts in one signature, and you later decide which commitments to open. The salt matters more than it looks — without it, a verifier could brute-force a hidden claim like "over 18: true" from a two-value guess space.'},
      tech:`<em>SD-JWT</em>: for each claim, issuer computes\n<em>hash( base64(salt, name, value) )</em> and puts the digest in <em>_sd[]</em>.\nThe JWS signs the digest array. Disclosures are held by the wallet\nand released individually. ISO mdoc does the equivalent with\n<em>IssuerSignedItem</em> digests in the <em>MSO</em>.`,
      fact:`<div class="kv"><b>Why salt</b><span>Stops brute-forcing low-entropy claims like a boolean or a postcode</span></div>
            <div class="kv"><b>Blinding</b><span>The digest array reveals how many claims exist, not what they are</span></div>`
    },
    {
      app:'EU Digital Identity Wallet', icon:'🇪🇺', right:'You decide',
      body: `<div class="h1p" style="font-size:19px">Your PID, claim by claim</div>
        <div class="pp" style="margin-bottom:13px">Tick what a verifier gets to see. Everything else leaves your phone as an unreadable hash — and the government's signature still checks out either way.</div>`,
      mount:'sd',
      primary: ok('See the verifier\'s side →','next'),
      secondary: ok('Back','back'),
      expl:{t:'Try the presets, then look at the meter',b:'Tap "Buying wine" and the verifier learns one fact out of ten. Tap "Bank onboarding" and it learns five — proportionate, because a regulated account genuinely needs them. Then tap "Reveal nothing" and notice what still holds: the verifier can confirm a valid government credential exists and is bound to this device, while learning nothing about you. That last state is not a party trick — it is the basis for pseudonymous but assured login.'},
      tech:`Wallet releases only the chosen <em>Disclosure</em> strings.\nUndisclosed claims travel as digests the verifier cannot invert.\nThe <em>Presentation Definition</em> from the verifier states what\nit wants; the wallet may return less and let the verifier refuse.`,
      fact:`<div class="kv"><b>Who decides</b><span>Verifier asks, holder chooses, verifier may reject</span></div>
            <div class="kv"><b>Product risk</b><span>Verifiers marking everything mandatory rebuilds over-collection</span></div>`
    },
    {
      app:'Lara Bank', icon:'🏦', right:'Verifying',
      body:`<div class="h1p" style="font-size:19px">What the verifier does with it</div>
        <div class="pp" style="margin-bottom:14px">Four checks, all local, all in milliseconds. No call to the Home Office at any point.</div>
        <div style="border:1px solid var(--line);background:#0e131f;border-radius:14px;padding:6px 14px">
        <div class="vstep" style="animation-delay:.05s"><div class="vn">1</div><div><b style="color:#e8edf7">Is the signature real?</b><br>Check the JWS against the Home Office public key, taken from the EU trusted list. Confirms the credential came from the state and has not been altered.</div></div>
        <div class="vstep" style="animation-delay:.25s"><div class="vn">2</div><div><b style="color:#e8edf7">Do the revealed values match what was signed?</b><br>Re-hash each disclosed claim with its salt and look for that digest in the signed list. A match proves the value is exactly what the issuer committed to.</div></div>
        <div class="vstep" style="animation-delay:.45s"><div class="vn">3</div><div><b style="color:#e8edf7">Is this the right person's wallet?</b><br>Verify the key-binding proof, signed over a nonce the verifier issued seconds ago. Stops a captured response being replayed.</div></div>
        <div class="vstep" style="animation-delay:.65s"><div class="vn">4</div><div><b style="color:#e8edf7">Is it still valid?</b><br>Check expiry, then check the status list for revocation.</div></div>
        </div>
        <div class="okbox" style="margin-top:14px">All four pass, so the bank knows the disclosed values are genuine government data, presented live, by the person they belong to. The claims it was not shown remain mathematically opaque — and it can prove that too, which matters when a regulator asks why it holds so little.</div>`,
      primary: ok('The catch →','next'),
      expl:{t:'Verification is offline and cheap',b:'Every check here is a local cryptographic operation against a public key the verifier already holds. No API call to an issuer, no per-check fee, no bilateral integration. That economics change is what makes cross-border and long-tail use cases viable — a Spanish car hire desk validating a DVLA credential costs nobody anything, which is why it can exist at all.'},
      tech:`1. JWS verify against issuer cert from the <em>Trusted List</em>\n2. Recompute <em>SHA-256</em> per disclosure, match against <em>_sd[]</em>\n3. Verify <em>KB-JWT</em> over verifier <em>nonce</em> + <em>aud</em>\n4. Check <em>exp</em>, then <em>Token Status List</em> index`,
      fact:`<div class="kv"><b>Cost per check</b><span>Effectively zero — no issuer call, no vendor transaction fee</span></div>
            <div class="kv"><b>Contrast</b><span>Bureau lookups and document-scan vendors charge per verification</span></div>`
    },
    {
      app:'EU Digital Identity Wallet', icon:'🇪🇺', right:'The catch',
      body:`<div class="h1p" style="font-size:19px">Where selective disclosure stops helping</div>
        <div class="pp" style="margin-bottom:14px">Three limits worth knowing before anyone in your organisation calls this solved.</div>
        <div class="warnbox" style="margin-bottom:10px"><b>1. Reveal one unique value and you are traceable again.</b> Disclose your document number to two different verifiers and they can link your visits by comparing notes. Minimising fields does not help if one of the fields you kept is an identifier.</div>
        <div class="warnbox" style="margin-bottom:10px"><b>2. The credential itself can be a fingerprint.</b> Present the same signed credential twice and the two presentations are trivially linkable — the signature is identical. Fixing this needs batch-issued one-time-use credentials, or proper zero-knowledge proofs. Neither is free.</div>
        <div class="warnbox"><b>3. The issuer decides your ceiling.</b> If DVLA had never minted <span class="mono" style="font-size:11px">age_over_18</span>, no amount of wallet cleverness could prove your age without revealing your birthday. Your privacy is capped by a schema decision made by someone else, years earlier.</div>
        <div class="spacer"></div>
        <div class="infobox">None of this makes selective disclosure a bad idea. It makes it a mechanism with sharp edges — and the edges are exactly where a bank designing its own attestations should be paying attention.</div>`,
      primary: ok('Next: catch a scam →','story:phish'),
      expl:{t:'What a smart skeptic would say',b:'They would say selective disclosure solves data minimisation, not unlinkability, and that the two get conflated in every vendor deck. They would be right. If Lara Bank issues an account attestation and every merchant sees the same signature, the bank has built a tracking token with a privacy story stapled to it. Batch issuance is the pragmatic answer available today; ZKP-based schemes are the durable one and are not yet at production scale in this ecosystem.'},
      tech:`Unlinkability options: <em>batch issuance</em> of single-use credentials\n(simple, costly in storage and refresh), or <em>BBS+</em> / ZKP signatures\n(elegant, immature tooling). The ARF anticipates both;\nmost 2026 deployments will ship batch issuance.`,
      fact:`<div class="kv"><b>Minimisation</b><span>Solved well today by SD-JWT and mdoc</span></div>
            <div class="kv"><b>Unlinkability</b><span>Only partly solved. Batch issuance is the current workaround.</span></div>
            <div class="kv"><b>For a bank</b><span>Design attestation schemas with predicates from day one</span></div>`
    }
  ]
},

{
  id:'phish', icon:'🎣', title:'A scammer tries it on', tag:'The bit nobody demos',
  blurb:'What happens when the request is fake.',
  steps:[
    {
      app:'Messages', icon:'💬', right:'Now',
      body:`<div class="reqcard" style="background:#0e1420">
          <div style="font-size:11px;color:var(--muted);margin-bottom:8px">SMS · +44 7•• ••• 9921</div>
          <div style="font-size:13px;line-height:1.6">LARA BANK: Unusual activity detected on account ••••4417. Verify your identity now to prevent suspension: <span style="color:var(--eu2)">lara-bank-secure.verify-id.co</span></div>
        </div>
        <div class="pp">It looks right. It arrived in the same thread as your real bank texts. Under time pressure, most people tap.</div>
        <div class="spacer"></div>
        <div class="pp sm" style="color:var(--muted)">Tap the link — go on, it's a demo.</div>`,
      primary: ok('Tap the link','next'),
      expl:{t:'The attack that actually works',b:'Impersonation fraud does not defeat cryptography, it defeats people. Any identity system that relies on the user spotting a fake will eventually lose. So the interesting question is not "is the wallet secure" — it is "what does the wallet do when the user has already been fooled".'},
      tech:`Classic smishing with SMS sender-ID spoofing into a trusted thread.`,
      fact:`<div class="kv"><b>UK context</b><span>APP fraud reimbursement rules put the cost of this on banks</span></div>`
    },
    {
      app:'EU Digital Identity Wallet', icon:'🇪🇺', right:'⚠ Warning',
      body:`<div class="h1p" style="font-size:18px;color:var(--warn)">Stop. This request is not legitimate.</div>
        ${verifier('❓','"Lara Bank Security"','verify-id.co · unknown entity',false,'')}
        <div class="warnbox">This site is asking for your full identity, but it is <b>not registered</b> as a verifier in the EU trust register. A real bank always is.<br><br>It also asked for your passport number and your photo — things a bank you already hold an account with would never need again.</div>
        <div class="spacer"></div>
        <div class="pp sm">Your wallet checked this before showing you anything. Nothing has been shared.</div>`,
      primary: ok('Block and report','next'),
      secondary: ok('Share anyway','next3'),
      expl:{t:'The trust register is the quiet hero',b:'Verifiers must register and hold an access certificate naming the attributes they may request. So the wallet can tell you two things no browser padlock ever could: who is really asking, and whether they are entitled to ask. The check happens before the user has to make a judgement call — which is the only place a security control belongs.'},
      tech:`Wallet validates the RP's <em>access certificate</em> against the\nnational registrar and the EU <em>Trusted List</em>. Unregistered RP,\nor a request exceeding the registered attribute scope, triggers this screen.`,
      fact:`<div class="kv"><b>Registration</b><span>Relying parties register with a Member State authority</span></div>
            <div class="kv"><b>Scope binding</b><span>Asking beyond your registered purpose is itself a red flag</span></div>`
    },
    {
      app:'EU Digital Identity Wallet', icon:'🇪🇺', right:'Blocked',
      body: okBlock('Blocked and reported') +
        `<div class="pp" style="text-align:center">Reported to your national registrar and to Lara Bank's fraud team. Nothing left your wallet.</div>
        <div class="okbox" style="margin-top:16px">Because the wallet holds the credentials, there was no password to phish and no document photo to steal. The attacker's best case was a warning screen.</div>
        <div class="spacer"></div>
        <div class="infobox">Honest caveat: this defends the identity moment. It does not stop someone talking you into <i>sending money</i>. Authorised push payment fraud is a different problem and the wallet does not solve it.</div>`,
      primary: ok('Next: sign something legally binding →','story:qes'),
      expl:{t:'Name what it does not fix',b:'Wallet advocates oversell. Impersonation fraud gets much harder. Social engineering that ends in a genuine, user-authorised payment gets no harder at all — and may get slightly worse, because a smoother identity layer can make a scam journey feel more legitimate. Plan for both.'},
      tech:`Reporting channel to national registrar; RP certificate revocation\npropagates to all wallets via the trusted list.`,
      fact:`<div class="kv"><b>Still unsolved</b><span>APP / authorised fraud, mule accounts, coercion</span></div>`
    }
  ]
},

{
  id:'qes', icon:'✍️', title:'Sign a mortgage', tag:'Qualified signature',
  blurb:'A signature with the legal weight of ink, done in 20 seconds.',
  steps:[
    {
      app:'Lara Bank', icon:'🏦', right:'Mortgage',
      body: heroBlock('📄','linear-gradient(135deg,#3d2a5f,#1d1733)') +
        `<div class="h1p">Your mortgage offer is ready to sign</div>
        <div class="pp">£412,000 over 25 years, fixed at 4.19% for 5 years. This is a legally binding contract.</div>
        <div class="spacer"></div>
        <div class="infobox">The old way: print 68 pages, sign, scan, post. Or attend a solicitor's office to sign in person. Days, sometimes weeks.</div>`,
      primary: ok('Review and sign','next'),
      expl:{t:'Not all e-signatures are equal',b:'Three tiers exist under eIDAS. A simple electronic signature is a typed name. An advanced one is uniquely linked to the signer. A qualified one — QES — is the only one that carries the same legal effect as a handwritten signature across every EU member state, and it reverses the burden of proof: the person disputing it has to show it is invalid.'},
      tech:`Signature tiers: <em>SES</em> → <em>AdES</em> → <em>QES</em>.\nQES requires a <em>QSCD</em> and a certificate from a <em>QTSP</em>\non the EU Trusted List.`,
      fact:`<div class="kv"><b>SES</b><span>Typed name, tick-box. Admissible but weak.</span></div>
            <div class="kv"><b>AdES</b><span>Linked to signer, tamper-evident. No automatic legal equivalence.</span></div>
            <div class="kv"><b>QES</b><span>Legal equivalence to wet ink, EU-wide. Art. 25(2).</span></div>`
    },
    {
      app:'Lara Bank', icon:'🏦', right:'Document',
      body:`<div class="doc">
          <h4>MORTGAGE DEED — LARA BANK PLC</h4>
          <div>Borrower: Laksh Singhal · Property: 42 Sandringham Road, London E8</div>
          <div class="ln"></div><div class="ln"></div><div class="ln s"></div>
          <div>Principal: £412,000 · Term: 300 months · Initial rate 4.19% fixed to 2031</div>
          <div class="ln"></div><div class="ln s"></div><div class="ln"></div><div class="ln s"></div>
          <div class="fade"></div>
        </div>
        <div class="pp sm" style="margin:12px 0 8px;color:var(--muted)">What you are about to sign, fingerprinted:</div>
        <div class="hashbox">SHA-256<br>a3f9e2 7b4c81 dd05a6 91fe33 20c7b8 e4419f 6a2d0c 88b715</div>
        <div class="pp sm" style="margin-top:10px">Change one comma in that document and this fingerprint changes completely. That is how anyone, forever, can prove nothing was altered after you signed.</div>`,
      primary: ok('I agree — sign this','next'),
      secondary: ok('Not now','back'),
      expl:{t:'You sign the hash, not the paper',b:'The signature is computed over the document\'s hash. That gives integrity for free: any later edit breaks the signature. It also means the signing service never needs the full document, which matters when the document is a mortgage deed and the service is a third party.'},
      tech:`<em>WYSIWYS</em> — what you see is what you sign.\nHash computed client-side; only the hash goes to the signing service.\nFormats: <em>PAdES</em> for PDF, <em>XAdES</em>, <em>CAdES</em>, <em>JAdES</em>.`,
      fact:`<div class="kv"><b>Common mistake</b><span>Signing a rendering, not the bytes the other party keeps</span></div>`
    },
    {
      app:'EU Digital Identity Wallet', icon:'🇪🇺', right:'QES',
      body:`<div class="h1p" style="font-size:18px;text-align:center">Authorise your qualified signature</div>
        ${scanScreen('✍️','Face ID + wallet PIN')}
        <div class="pp sm" style="text-align:center;margin-top:12px">Two factors, because this one is binding. Your wallet holds the only key that can produce your signature — the bank cannot, and neither can the signing provider.</div>
        <div class="progbar"><b id="qesbar"></b></div>
        <div class="pp sm" style="text-align:center;color:var(--muted)" id="qeslbl">Contacting qualified trust service provider…</div>`,
      auto:3200, primary: ok('Continue','next'), progress:'qes',
      expl:{t:'Sole control is the legal hinge',b:'QES only holds up because you, and nobody else, can trigger the signature. Remote signing keeps the key in a certified device at a trust service provider, but the activation data lives with you. If a provider could sign without you, the legal equivalence collapses — which is why this screen is deliberately heavier than a face unlock for a login.'},
      tech:`Remote QSCD at a <em>QTSP</em>. Signature activation data held by the wallet;\nprotocol per <em>CEN EN 419 241-2</em>. Wallet acts as the\n<em>signature activation module</em>. ETSI EN 319 series defines the formats.`,
      fact:`<div class="kv"><b>Wallet duty</b><span>Every EUDI wallet must be able to create QES, free for personal use</span></div>
            <div class="kv"><b>Why that matters</b><span>QES cost per signature has been the main barrier to adoption</span></div>`
    },
    {
      app:'Lara Bank', icon:'🏦', right:'Signed',
      body:`<div class="doc">
          <h4>MORTGAGE DEED — LARA BANK PLC</h4>
          <div>Borrower: Laksh Singhal · Property: 42 Sandringham Road, London E8</div>
          <div class="ln"></div><div class="ln s"></div><div class="ln"></div>
        </div>
        <div class="seal">QUALIFIED<br><b style="font-size:11px">e-SIGNATURE</b><br>L. Singhal<br>10 Aug 2026 09:41 UTC</div>
        <div style="clear:both;height:8px"></div>
        <div class="okbox">Signed. Legally equivalent to a handwritten signature in all 27 member states, and in the UK under the retained regime.</div>
        <div class="spacer"></div>
        <div class="kv"><b>Signer</b><span>Verified to LoA High via PID</span></div>
        <div class="kv"><b>Certificate</b><span>Qualified, issued by an EU-listed QTSP</span></div>
        <div class="kv"><b>Timestamp</b><span>Qualified time stamp, RFC 3161</span></div>
        <div class="kv"><b>Validity</b><span>Verifiable for decades — long-term validation embedded</span></div>
        ${compare('9 days','Print, post, solicitor','20 sec','QES from your wallet')}`,
      primary: ok('Next: cross the border →','story:travel'),
      expl:{t:'Long-term validation is the unglamorous requirement',b:'A mortgage outlives the certificate that signed it. Without embedded revocation data and trusted timestamps, in ten years nobody can tell whether the certificate was valid at signing. LTV formats (PAdES B-LTA) solve this, and skipping it is the most common way an e-signature programme quietly fails an audit years later.'},
      tech:`<em>PAdES B-LTA</em>: signature + OCSP/CRL evidence + qualified\ntimestamp, re-stamped over time. Validation follows <em>ETSI TS 119 102</em>.`,
      fact:`<div class="kv"><b>Art. 25(2)</b><span>QES has the equivalent legal effect of a handwritten signature</span></div>
            <div class="kv"><b>Art. 25(3)</b><span>A QES from one member state is valid in all others</span></div>`
    }
  ]
},

{
  id:'travel', icon:'✈️', title:'Rent a car in Spain', tag:'Cross-border',
  blurb:'A British licence, a Spanish desk, no translation.',
  steps:[
    {
      app:'Alquiler Málaga', icon:'🚗', right:'Pick-up',
      body: heroBlock('🚗','linear-gradient(135deg,#1d3a7a,#0f4038)') +
        `<div class="h1p">Collect your car — Málaga Airport</div>
        <div class="pp">The desk needs to check your driving licence is valid and covers this vehicle class. Normally: queue, hand over the plastic, wait while someone squints at a licence issued in another country.</div>`,
      primary: ok('Present my licence','next'),
      expl:{t:'Cross-border is where paper fails',b:'A Spanish rental clerk cannot meaningfully validate a British licence. They check that it looks like one. Digital credentials replace visual familiarity with a signature check that works identically regardless of which country issued the credential.'},
      tech:`<em>ISO/IEC 18013-5</em> mDL presentation over BLE or NFC, offline-capable.`,
      fact:`<div class="kv"><b>Offline</b><span>mDL presentation works with no network on either device</span></div>`
    },
    {
      app:'EU Digital Identity Wallet', icon:'🇪🇺', right:'Request',
      body:`<div class="h1p" style="font-size:18px">Alquiler Málaga is asking</div>
        ${verifier('🚗','Alquiler Málaga S.L.','Registered vehicle rental · Andalucía',true,'')}
        ${fields([
          {k:'Licence categories',v:'B, BE'},
          {k:'Valid until',v:'2031'},
          {k:'Photo',v:'For the desk to match your face'},
          {k:'Full name',v:'Laksh Singhal', opt:true}
        ])}
        ${withheld(['Your home address','Your date of birth','Your licence number','Any endorsements or points','Your other credentials'])}
        <div class="infobox" style="margin-top:12px">Tap the toggle to withhold your name and watch the request still succeed. The rental company genuinely does not need it to verify you can drive.</div>`,
      primary: ok('Share','next'),
      secondary: ok('Cancel','back'),
      expl:{t:'Try the toggle',b:'Optional attributes are a design decision, not a technical one. Whoever writes the presentation request decides what is mandatory. Get this wrong and you have rebuilt over-collection on better plumbing — which is the most likely way this whole programme disappoints in practice.'},
      tech:`Verifier device reads mdoc over BLE. Reader authentication proves\nthe reader is a registered device before any data is released.`,
      fact:`<div class="kv"><b>Watch for</b><span>Relying parties marking everything "required" out of habit</span></div>`
    },
    {
      app:'Alquiler Málaga', icon:'🚗', right:'Verified',
      body: okBlock('Licence verified') +
        `<div class="pp" style="text-align:center">Bay 14 · Seat León · Keys in the app.<br>You walked past the queue.</div>
        <div class="okbox" style="margin-top:16px">Same wallet, same tap, a different country and a different language. The rental company verified a DVLA signature it has never seen before, in under a second, with no bilateral agreement between the UK and Spain needed for the check itself.</div>
        <div class="spacer"></div>
        <div class="infobox">The honest caveat: UK–EU mutual recognition is a live policy question. The UK's DIATF and the EU's eIDAS 2.0 solve the same problem with different trust anchors, and bridging them is unfinished business.</div>`,
      primary: ok('Next: see who has your data →','story:control'),
      expl:{t:'Two regimes, not one',b:'The UK built a trust framework around certified providers and a governing body. The EU built a wallet mandate around member-state issuers. Both work. They do not automatically talk to each other. Any UK bank operating in both markets should plan for two identity postures rather than one with carve-outs.'},
      tech:`UK: <em>DIATF</em> certified IDSPs, attribute exchange.\nEU: <em>EUDI Wallet</em>, member-state issued PID, EU trusted lists.\nBridging requires mutual recognition arrangements not yet complete.`,
      fact:`<div class="kv"><b>UK framework</b><span>Digital Identity and Attributes Trust Framework (DIATF)</span></div>
            <div class="kv"><b>Legal footing</b><span>Data (Use and Access) Act put DIATF on a statutory basis</span></div>`
    }
  ]
},

{
  id:'control', icon:'🎛️', title:'Take it all back', tag:'Control, visibly',
  blurb:'See everywhere you used it. Revoke in one tap.',
  steps:[
    {
      app:'EU Digital Identity Wallet', icon:'🇪🇺', right:'Activity',
      body:`<div class="h1p" style="font-size:19px">Everywhere you've proved something</div>
        <div class="pp" style="margin-bottom:14px">Kept on your phone. Not on anyone's server. Nobody can see this list but you.</div>
        ${[
          ['🏦','Lara Bank','Name, DOB, nationality, address','Today, 09:41'],
          ['🍷','Vintners Direct','Over 18 only','Today, 09:38'],
          ['🚗','Alquiler Málaga','Licence categories, validity, photo','2 Aug'],
          ['⚕️','Hospital Costa del Sol','Health insurance cover','1 Aug'],
          ['🏛️','HMRC','Name, NI number','24 Jul']
        ].map(r=>`<div class="field" style="align-items:flex-start">
            <div style="font-size:18px;margin-top:2px">${r[0]}</div>
            <div><div class="fv" style="font-size:13px">${r[1]}</div>
            <div class="fk" style="margin-top:3px">${r[2]}</div></div>
            <div class="lock" style="align-self:center">${r[3]}</div></div>`).join('')}`,
      primary: ok('Manage Lara Bank','next'),
      expl:{t:'Transparency you can act on',b:'Most privacy dashboards tell you what a company decided to record. This one is generated by your own device, from your own actions, and the issuers cannot see it. That asymmetry — the log lives with the user — is what makes it trustworthy rather than performative.'},
      tech:`Local transaction log in the wallet. Issuers receive no notification\nof presentations, preventing issuer-side tracking (unlinkability).`,
      fact:`<div class="kv"><b>Contrast</b><span>Federated login lets the identity provider see every site you visit</span></div>`
    },
    {
      app:'EU Digital Identity Wallet', icon:'🇪🇺', right:'Lara Bank',
      body:`<div class="h1p" style="font-size:18px">Lara Bank</div>
        <div class="pp" style="margin-bottom:12px">Holds 4 attributes you shared on 10 August 2026.</div>
        ${fields([
          {k:'Full name',v:'Laksh Singhal'},
          {k:'Date of birth',v:'14 March 1985'},
          {k:'Nationality',v:'United Kingdom'},
          {k:'Current address',v:'42 Sandringham Rd, London E8'}
        ])}
        <div class="spacer"></div>
        <div class="infobox">You can request erasure straight from here. Where the bank must keep records to satisfy anti-money-laundering law, it will tell you which ones and for how long — instead of ignoring the request.</div>`,
      primary: ok('Request erasure','next'),
      secondary: ok('Back','back'),
      expl:{t:'Where user control meets regulation',b:'Erasure is not absolute. A bank must retain KYC records for five years after the relationship ends under money-laundering rules, and that obligation beats a deletion request. The design honesty here matters: show the user what can go, what must stay, and why. Pretending everything is erasable is how you end up with a complaint you cannot defend.'},
      tech:`GDPR Art. 17 request routed to the RP. RP responds with retained\nitems and legal basis — MLR 2017 / AMLD retention overrides erasure.`,
      fact:`<div class="kv"><b>UK retention</b><span>5 years after end of relationship (MLR 2017)</span></div>
            <div class="kv"><b>Tension</b><span>Right to erasure vs AML record-keeping duty</span></div>`
    },
    {
      app:'EU Digital Identity Wallet', icon:'🇪🇺', right:'Done',
      body: okBlock('Request sent') +
        `<div class="pp" style="text-align:center">Lara Bank has 30 days to respond.</div>
        <div class="spacer"></div>
        <div class="okbox"><b>Deleted immediately:</b> mobile number, marketing preferences.</div>
        <div style="height:9px"></div>
        <div class="warnbox"><b>Retained until 2031:</b> name, date of birth, nationality, address — required by anti-money-laundering law for five years after your account closes. Locked, not usable for anything else.</div>
        <div class="spacer"></div>
        <div class="pp sm" style="color:var(--muted)">That is the honest version. A wallet gives you control over what you share and visibility over where it went. It does not repeal financial crime law.</div>`,
      primary: ok('Start over','story:setup'),
      expl:{t:'The closing argument',b:'The wallet does not make regulation disappear. It moves the point of control to the person, makes over-collection technically unnecessary, and turns a document-inspection problem into a signature-checking one. Those three changes are enough to reshape onboarding, age assurance and contract signing — and you just tapped through all three.'},
      tech:`End of demo. Everything shown maps to published EUDI Wallet ARF flows.`,
      fact:`<div class="kv"><b>Wallets live</b><span>Member states to offer wallets from 2026</span></div>
            <div class="kv"><b>Acceptance</b><span>Regulated sectors including banking obliged to accept</span></div>
            <div class="kv"><b>AMLR</b><span>EU AML regulation applies from 2027 — reusable verified identity fits it</span></div>`
    }
  ]
}
];
export const BAND: Record<string, BandEntry> = {

'setup:0':{cap:'Every single flow in this demo has the same three parties. An <b>issuer</b> vouches for a fact. <b>You</b> hold the proof. A <b>verifier</b> asks for it. Nothing else is going on.'},

'setup:1':{iss:'HM Passport Office', issIcon:'🛂', issDesc:'Signed your passport chip when it was made',
  flow:'iss>you', label:'Government signature, read from the chip',
  cap:'The Home Office signed this data years ago. Reading the chip does <b>not</b> contact them — the signature travels with the document.'},

'setup:2':{cap:'No third party at all here. Your phone compares your face to the chip photo. This step is you proving you are you, to yourself.'},

'setup:3':{iss:'HM Passport Office', issIcon:'🛂', issDesc:'The state. The only party that can assert legal identity.',
  flow:'iss>you', label:'PID issued into your wallet',
  cap:'Your <b>PID</b> is the root credential. Only the state can issue it, and every other credential you collect will be built on top of it.'},

'setup:4':{iss:'5 issuers', issIcon:'🏛️', issDesc:'Passport Office, DVLA, Lara Bank, NHS, your university',
  flow:'iss>you', label:'Signed credentials handed to your wallet',
  cap:'Each issuer signs only what it is authoritative for, hands it over, and <b>steps out of the picture</b>. From now on they are not involved when you use it.'},

'issue:0':{ver:'DVLA', verIcon:'🚗', verDesc:'About to act as a verifier — not yet an issuer',
  cap:'DVLA starts on the <b>right</b>. Before it can give you anything, it has to be sure who you are.'},

'issue:1':{iss:'HM Passport Office', issIcon:'🛂', issDesc:'Signed your PID. Not contacted now.',
  ver:'DVLA', verIcon:'🚗', verDesc:'Verifier. Asking for PID attributes to find your record.',
  flow:'ver>you', label:'Request: name, date of birth, address',
  cap:'Three parties on screen at once. The Passport Office signed the data, <b>you</b> hold it, and DVLA is asking for it — exactly like Lara Bank did.'},

'issue:2':{iss:'DVLA', issIcon:'🚗', issDesc:'Same organisation. It has just changed role.',
  ver:'DVLA', verIcon:'🚗', verDesc:'Verification finished. Stepping down from this seat.',
  cap:'The switch. DVLA has appeared on the <b>left</b> as an issuer while still fading from the right. <b>Roles belong to moments, not organisations.</b>'},

'issue:3':{iss:'DVLA', issIcon:'🚗', issDesc:'Issuer. Signs your licence and binds it to this phone.',
  flow:'iss>you', label:'Signed mDL, bound to your device key',
  cap:'DVLA is now purely an <b>issuer</b>. It hands the credential over and, as with every issuer, it will not be involved when you use it.'},

'issue:4':{iss:'DVLA', issIcon:'🚗', issDesc:'Publishes a status list. Never learns who checks it.',
  flow:'iss>you', label:'Status list — one bit flipped to revoked',
  cap:'Revocation flows from issuer to <b>everyone</b>, through a public list. DVLA does not learn which verifier looked you up.'},

'disclose:0':{iss:'HM Passport Office', issIcon:'🛂', issDesc:'Salted and hashed each claim separately at issuance',
  flow:'iss>you', label:'One signature over ten claim hashes',
  cap:'Everything on the phone right now was decided <b>at issuance</b>, by the issuer. This screen is the reason the next one is possible.'},

'disclose:1':{cap:'No issuer. No verifier. Just you and your phone deciding what a future verifier will be allowed to see. <b>The choice happens here</b>, not in anyone else\'s system.'},

'disclose:2':{iss:'HM Passport Office', issIcon:'🛂', issDesc:'Public key on the EU trusted list. Not contacted.',
  ver:'Lara Bank', verIcon:'🏦', verDesc:'Runs four local checks. No network call to the issuer.',
  flow:'you>ver', label:'Disclosed claims + hidden digests + proof of key',
  cap:'The verifier proves the data is genuine <b>using only maths and a public key</b>. This is why cross-border verification costs nothing per check.'},

'disclose:3':{cap:'The limits are structural, not bugs. Two of the three are decided by the <b>issuer</b> long before you ever open your wallet.'},

'bank:0':{iss:'HM Passport Office', issIcon:'🛂', issDesc:'Already signed your identity, months ago',
  ver:'Lara Bank', verIcon:'🏦', verDesc:'Wants proof of who you are before opening an account',
  cap:'Lara Bank is the <b>verifier</b> — the party asking. Right now it knows nothing about you.'},

'bank:1':{iss:'HM Passport Office', issIcon:'🛂', issDesc:'Not contacted. Not notified. Does not know.',
  ver:'Lara Bank', verIcon:'🏦', verDesc:'Registered verifier, entitled to ask for these attributes',
  flow:'ver>you', label:'Request: 5 named attributes',
  cap:'The request goes to <b>your wallet</b>, not to the government. This is the part people expect to work the other way round.'},

'bank:2':{iss:'HM Passport Office', issIcon:'🛂', issDesc:'Still not involved',
  ver:'Lara Bank', verIcon:'🏦', verDesc:'Waiting. It cannot proceed without you.',
  cap:'The decision happens on your device. Neither the issuer nor the verifier can release this data — <b>only you can</b>.'},

'bank:3':{iss:'HM Passport Office', issIcon:'🛂', issDesc:'Never contacted at any point in this flow',
  ver:'Lara Bank', verIcon:'🏦', verDesc:'Verified the government signature offline, in milliseconds',
  flow:'you>ver', label:'Signed attributes + proof of possession',
  cap:'Lara Bank trusted the Home Office <b>without ever calling the Home Office</b>. That single property is what removes the queue, the callout fee and the three-day wait.'},

'age:0':{iss:'HM Passport Office', issIcon:'🛂', issDesc:'Signed your date of birth once, long ago',
  ver:'Vintners Direct', verIcon:'🍷', verDesc:'Licensed retailer. Needs an answer, not your file.',
  cap:'Same issuer as the bank story. Different verifier. <b>Your wallet did not need re-issuing</b> to serve a completely different use case.'},

'age:1':{iss:'HM Passport Office', issIcon:'🛂', issDesc:'Not contacted. Cannot see this happening.',
  ver:'Vintners Direct', verIcon:'🍷', verDesc:'Asking one boolean question',
  flow:'ver>you', label:'Request: are you over 18?',
  cap:'The wallet derives <b>over 18</b> from a birth date it never reveals, and the issuer signature still checks out. Proof without exposure.'},

'age:2':{iss:'HM Passport Office', issIcon:'🛂', issDesc:'Has no idea you bought wine. By design.',
  ver:'Vintners Direct', verIcon:'🍷', verDesc:'Holds a signed proof, and no personal data',
  flow:'you>ver', label:'"Over 18 = true", government-signed',
  cap:'The retailer verified a Home Office signature. The Home Office learned nothing. That gap is called <b>unlinkability</b>, and federated login cannot do it.'},

'phish:0':{ver:'"Lara Bank Security"', verIcon:'❓', verDesc:'Claims to be your bank. Is not.', verBad:true,
  cap:'Someone is impersonating a <b>verifier</b>. Note the attack surface: they are not attacking the wallet, they are attacking your judgement.'},

'phish:1':{iss:'EU Trust Register', issIcon:'🗂️', issRole:'Trust register', issDesc:'The public list of who is allowed to ask you for what',
  ver:'verify-id.co', verIcon:'❓', verDesc:'Not on the register. Asking for more than any bank needs.', verBad:true,
  flow:'iss>you', label:'Lookup: is this verifier registered?',
  cap:'A fourth role appears only here. Your wallet checked the <b>register</b> before it showed you anything — so the security decision was made before you had a chance to get it wrong.'},

'phish:2':{iss:'EU Trust Register', issIcon:'🗂️', issRole:'Trust register', issDesc:'Receives the report; can revoke a certificate EU-wide',
  ver:'verify-id.co', verIcon:'🚫', verDesc:'Blocked. Received nothing.', verBad:true,
  flow:'you>iss', label:'Report filed',
  cap:'There was no password to phish and no document photo to steal. The attacker\'s <b>best possible outcome</b> was a warning screen.'},

'qes:0':{iss:'Qualified Trust Service Provider', issIcon:'🔏', issRole:'QTSP — issuer of trust', issDesc:'Issues your qualified certificate and holds the signing key in certified hardware',
  ver:'Lara Bank', verIcon:'🏦', verDesc:'Needs a signature it can rely on in court',
  cap:'A new issuer enters: the <b>QTSP</b>. It does not vouch for a fact about you — it vouches for your <b>signature</b>. Same pattern, different payload.'},

'qes:1':{iss:'Qualified Trust Service Provider', issIcon:'🔏', issRole:'QTSP — issuer of trust', issDesc:'Not yet involved',
  ver:'Lara Bank', verIcon:'🏦', verDesc:'Sends the document; keeps the original',
  flow:'ver>you', label:'Document hash to be signed',
  cap:'Only the <b>fingerprint</b> travels. Your mortgage deed does not get emailed around, and the QTSP never sees its contents.'},

'qes:2':{iss:'Qualified Trust Service Provider', issIcon:'🔏', issRole:'QTSP — issuer of trust', issDesc:'Holds the key, but cannot use it without you',
  ver:'Lara Bank', verIcon:'🏦', verDesc:'Waiting',
  flow:'you>iss', label:'Authorisation to activate your signing key',
  cap:'This is the legal hinge. The QTSP holds the key; <b>only your wallet can activate it</b>. If the provider could sign alone, the legal equivalence to wet ink collapses.'},

'qes:3':{iss:'Qualified Trust Service Provider', issIcon:'🔏', issRole:'QTSP — issuer of trust', issDesc:'On the EU trusted list — checkable for decades',
  ver:'Lara Bank', verIcon:'🏦', verDesc:'Holds a signature enforceable in all 27 member states',
  flow:'you>ver', label:'Qualified signature + qualified timestamp',
  cap:'Lara Bank validates the signature against the EU trusted list. Again: <b>it never phones the QTSP</b>. The trust is carried in the certificate chain.'},

'travel:0':{iss:'DVLA', issIcon:'🚗', issDesc:'A British issuer. Signed your licence categories.',
  ver:'Alquiler Málaga', verIcon:'🅿️', verDesc:'A Spanish verifier. Has never dealt with DVLA.',
  cap:'A British issuer and a Spanish verifier with <b>no relationship whatsoever</b>. Under paper rules, the clerk can only check that your licence looks plausible.'},

'travel:1':{iss:'DVLA', issIcon:'🚗', issDesc:'Closed for the weekend. Irrelevant.',
  ver:'Alquiler Málaga', verIcon:'🅿️', verDesc:'Registered rental company, asking via a certified reader',
  flow:'ver>you', label:'Request: categories, validity, photo',
  cap:'Notice the toggle on the phone. Whoever writes the request decides what is mandatory — <b>which is where this programme can quietly fail</b> if verifiers mark everything required.'},

'travel:2':{iss:'DVLA', issIcon:'🚗', issDesc:'Not contacted. No cross-border data-sharing agreement used.',
  ver:'Alquiler Málaga', verIcon:'🅿️', verDesc:'Verified a DVLA signature it had never seen before, offline',
  flow:'you>ver', label:'Signed licence attributes',
  cap:'This worked with <b>no network on either device</b>. Cross-border verification became a signature check rather than a diplomatic arrangement.'},

'control:0':{cap:'Both nodes are dark, and that is the point. This log is generated by <b>your device, from your actions</b>. No issuer and no verifier can see it.'},

'control:1':{ver:'Lara Bank', verIcon:'🏦', verDesc:'Holds 4 attributes you gave it on 10 August',
  cap:'You are now dealing with the <b>verifier</b> directly. The issuer has no role in what a verifier does with data after you shared it.'},

'control:2':{ver:'Lara Bank', verIcon:'🏦', verDesc:'Must answer within 30 days — and must keep some of it anyway',
  flow:'you>ver', label:'Erasure request',
  cap:'The wallet moved <b>control</b> to you. It did not repeal anti-money-laundering law, and any honest version of this demo has to say so.'}

};

export const BAND_DEFAULT_ISS: { role: string; name: string; desc: string; icon: string } = {
  role: "Issuer",
  name: "Not involved here",
  desc: "Vouches for a fact about you, then walks away",
  icon: "🏛️",
};
export const BAND_DEFAULT_VER: { role: string; name: string; desc: string; icon: string } = {
  role: "Verifier",
  name: "Not involved here",
  desc: "Asks you to prove something before it serves you",
  icon: "🔎",
};
