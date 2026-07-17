// Typed AR/EN string dictionary. Every user-facing string in the app is a key
// here — components call t("some.key") from LangProvider rather than hardcoding
// text, so the whole app can switch language at runtime (DESIGN_SYSTEM.md §7, §12).
//
// Numbers stay Western digits + tabular-nums in both languages (§3.2) — never
// interpolate an Arabic-Indic digit through these templates.
//
// A few entries are flagged below with "REVIEW:" — best-effort translations of
// specialized banking/regulatory phrasing that a native/domain reviewer should
// double-check before this ships.
export const STRINGS = {
  // --- brand ---
  "brand.wordmark": { ar: "جدوى", en: "Jadwa" },

  // --- public landing page (LandingPage, "/") ---
  // Copy ported verbatim from design-mocks/jadwa_landing_redesign.html (the
  // visual + copy source of truth for this page) — no hyphens or dashes, per
  // the copy rule; open compounds throughout ("bank ready", "stress tested").
  "landing.nav.platform": { ar: "المنصّة", en: "Platform" },
  "landing.nav.howItWorks": { ar: "كيف تعمل", en: "How it works" },
  "landing.nav.dataSources": { ar: "المصادر", en: "Data sources" },
  "landing.cta.getStarted": { ar: "ابدأ الآن", en: "Get started" },

  "landing.hero.eyebrow": {
    ar: "الجدارة الائتمانية للمنشآت، مُتحقّقة",
    en: "Verified SME underwriting",
  },
  "landing.hero.title": {
    ar: "دراسة جدوى حيّة لكل طلب تمويل",
    en: "A living feasibility study for every financing application",
  },
  "landing.hero.body": {
    ar: "من فواتير متناثرة إلى قرار تمويل يمكنك الدفاع عنه. تقرأ جدوى كل مستند، وتطابقه مع السجل البنكي، وتختبر المنشأة تحت الضغط قبل أن يوقّع أحد.",
    en: "From scattered invoices to a lending decision you can defend. Jadwa reads every document, reconciles it against the bank ledger, and stress tests the business before anyone signs.",
  },
  "landing.hero.cta": { ar: "ابدأ طلبك", en: "Get started" },
  "landing.trust.chip.zatca": { ar: "متوافق مع فاتورة ZATCA", en: "ZATCA aware" },
  "landing.trust.chip.bilingual": { ar: "عربي وإنجليزي", en: "Arabic and English" },
  "landing.trust.chip.data": { ar: "بيانات سعودية رسمية", en: "Official Saudi data" },

  "landing.platform.eyebrow": { ar: "المنصّة", en: "The platform" },
  "landing.platform.title": {
    ar: "مسار واحد. جمهوران. طبقة ثقة مشتركة.",
    en: "One pipeline. Two audiences. One shared layer of trust.",
  },
  "landing.platform.body1": {
    ar: "يتعثّر التمويل في الفجوة بين طرفين لا يثق أحدهما بالآخر تمامًا. المنشأة تعرف أن أرقامها حقيقية لكنها لا تستطيع إثبات ذلك بسرعة، والبنك يريد أن يصدّقها لكنه لا يستطيع التحقق منها على نطاق واسع. تقف جدوى في هذه الفجوة كطبقة محايدة تقوم على الأدلة أولًا، فتحوّل الفواتير والكشوف الخام إلى صورة مالية منظّمة ومُتحقّقة، ثم تعرض الصورة نفسها على كل طرف باللغة التي يحتاجها.",
    en: "Financing stalls in the gap between two parties who do not fully trust each other. A business knows its numbers are real but cannot prove it quickly. A bank wants to believe them but cannot verify them at scale. Jadwa sits in that gap as a neutral, evidence first layer. It turns raw invoices and statements into a structured, verified financial picture, then presents that same picture to each side in the language it needs.",
  },
  "landing.platform.body2Lead": { ar: "لا شيء يُؤخذ على الثقة.", en: "Nothing is taken on faith." },
  "landing.platform.body2Rest": {
    ar: " كل رقم يُطابَق مع سجل المعاملات الفعلي، وكل فاتورة يُتحقَّق من صحتها، وكل نموذج عمل يُختبَر أمام الصدمات الأكثر احتمالًا في قطاعه. ما يصل إلى البنك ليس ادعاءً، بل نتيجة.",
    en: " Every figure is matched against real transaction history, every invoice is checked for authenticity, and every business model is tested against the shocks most likely to hit its sector. What reaches the bank is not a claim. It is a conclusion.",
  },

  "landing.pipeline.title": { ar: "كيف تعمل جدوى", en: "How Jadwa works" },
  "landing.pipeline.subtitle": {
    ar: "ست مراحل تعمل تلقائيًا على كل مستند يصل",
    en: "Six stages, running automatically on every document that arrives",
  },
  "landing.stage.extract": { ar: "استخراج", en: "Extract" },
  "landing.stage.forensic": { ar: "تدقيق", en: "Forensic" },
  "landing.stage.stressTest": { ar: "اختبار الضغط", en: "Stress test" },
  "landing.stage.market": { ar: "السوق", en: "Market" },
  "landing.stage.riskModel": { ar: "نموذج المخاطر", en: "Risk model" },
  "landing.stage.record": { ar: "السجل", en: "Record" },

  "landing.sme.eyebrow": { ar: "لأصحاب الأعمال", en: "For business owners" },
  "landing.sme.title": {
    ar: "ادخل بمستنداتك، واخرج بطلب جاهز للبنك.",
    en: "Walk in with documents. Walk out with a bank ready application.",
  },
  "landing.sme.body": {
    ar: "تخسر كثير من المنشآت الصغيرة التمويل لا لأنها ضعيفة، بل لأن أوراقها متناثرة بين صيغ ولغات ومجلدات. تقبل جدوى ذلك كله، بالعربية أو الإنجليزية، مصوَّرًا أو ممسوحًا، وتنظّمه في طلب واحد نظيف خلال دقائق. وقبل أن ترسل، ترى تمامًا ما سيراه البنك، بما في ذلك نقاط الضعف التي سيثيرها موظف دقيق، لتعالجها أولًا.",
    en: "Many small businesses lose financing not because they are weak, but because their paperwork is scattered across formats, languages, and folders. Jadwa accepts all of it, Arabic or English, photographed or scanned, and organizes it into one clean application in minutes. Before you submit, you see exactly what a bank will see, including the weaknesses a careful officer would raise, so you can address them first.",
  },
  "landing.sme.cta": { ar: "ابدأ طلبك", en: "Start an application" },
  "landing.sme.check1": {
    ar: "رفع الفواتير والكشوف بأي صيغة",
    en: "Upload invoices and statements in any format",
  },
  "landing.sme.check2": {
    ar: "قراءة تلقائية بالعربية والإنجليزية",
    en: "Automatic reading in Arabic and English",
  },
  "landing.sme.check3": {
    ar: "ملخّص صحّة مالية بلغة واضحة قبل الإرسال",
    en: "A plain language health summary before you submit",
  },
  "landing.sme.check4": { ar: "ملف طلب جاهز للبنك", en: "A generated, bank ready application file" },

  "landing.bank.eyebrow": { ar: "للبنوك", en: "For banks" },
  "landing.bank.title": {
    ar: "قرارك على الأدلة، لا على الثقة.",
    en: "Underwrite on evidence, not on trust.",
  },
  "landing.bank.body": {
    ar: "يقضي الموظفون ساعات في قراءة تقارير جامدة لا يزالون مضطرين للتشكيك فيها. تسلّمهم جدوى ملفًا مُقيَّمًا مسبقًا أُنجز فيه العمل الشاق. يصل كل طلب مُدقّقًا جنائيًا، ومختبَرًا تحت الضغط، ومستندًا إلى بيانات السوق السعودي، مع إشارة واضحة على مدى الأصالة. ويمكن للموظف استكشاف المخاطر تفاعليًا، فيحرّك عوامل السيناريو ويراقب الملف وهو يتغيّر، ثم يقرّر والدليل بين يديه.",
    en: "Officers spend hours reading static reports they still have to second guess. Jadwa hands them a pre scored file where the hard work is already done. Every application arrives forensically checked, stress tested, and grounded in Saudi market data, with a clear signal on authenticity. Officers can explore the risk interactively, moving scenario levers and watching the profile respond, then decide with the evidence in front of them.",
  },
  "landing.bank.cta": { ar: "دخول لوحة البنك", en: "Open the bank dashboard" },
  "landing.bank.check1": {
    ar: "قائمة طلبات مُقيَّمة مسبقًا",
    en: "A pre scored queue of submitted applications",
  },
  "landing.bank.check2": {
    ar: "فحوص أصالة جنائية بإشارات واضحة",
    en: "Forensic authenticity checks with clear flags",
  },
  "landing.bank.check3": {
    ar: "سيناريوهات مخاطر تفاعلية تُحسب فورًا",
    en: "Interactive risk scenarios that recalculate live",
  },
  "landing.bank.check4": {
    ar: "سياق سوقي مستند إلى بيانات سعودية رسمية",
    en: "Market context grounded in official Saudi data",
  },

  "landing.verdict.line": { ar: "كل رقم تدقّقه جدوى", en: "Every figure cross checked by Jadwa" },
  "landing.trust.body": {
    ar: "كل رقم في كل طلب يمرّ بمطابقة السجل البنكي، والتحقق من رمز فاتورة ZATCA، واختبار الضغط قبل أن يصل إلى مكتبك.",
    en: "Every figure in every application passes ledger reconciliation, ZATCA verification, and stress testing before it reaches your desk.",
  },

  "landing.closing.title": { ar: "ثقة في كل قرار تمويل.", en: "Bring trust to every financing decision." },
  "landing.closing.body": {
    ar: "ابدأ كمنشأة تبحث عن تمويل، أو سجّل الدخول إلى لوحة البنك.",
    en: "Start as a business seeking financing, or sign in to the bank dashboard.",
  },

  "landing.footer.rights": { ar: "© {{year}} جدوى", en: "© {{year}} Jadwa" },

  // --- public data-sources / credibility page (DataSourcesPage, "/data") ---
  // SKELETON pass only — structure + honest placeholders, no real coverage
  // numbers (the corpus isn't ingested yet). Never say "trained on" anywhere
  // here: it's retrieval (RAG) over a corpus, nothing is trained/fine-tuned.
  "data.hero.eyebrow": { ar: "المصادر", en: "Data sources" },
  "data.hero.title": { ar: "مبني على بيانات سعودية رسمية وعامة", en: "Grounded in official Saudi public data" },
  "data.hero.body": {
    ar: "يعتمد جدوى على الاسترجاع المعزز بالتوليد فوق مجموعة مختارة من المصادر الرسمية العامة. كل استنتاج مرتبط بمصدره ويُستشهد به.",
    en: "Jadwa uses retrieval augmented generation over a curated set of official public sources. Every insight is grounded in and cites its source.",
  },
  "data.sources.title": { ar: "المصادر", en: "Sources" },
  "data.sources.subtitle": {
    ar: "التغطية الكاملة قيد الإضافة. القائمة أدناه تعكس البنية المخطط لها فقط.",
    en: "Full coverage is still being added. The list below reflects the planned structure only.",
  },
  "data.sources.coveragePending": { ar: "التغطية: قيد الإدراج", en: "Coverage: pending ingestion" },
  "data.source.sama.name": { ar: "البنك المركزي السعودي (ساما)", en: "Saudi Central Bank (SAMA)" },
  "data.source.sama.body": {
    ar: "منشورات تنظيمية ومصرفية، ومرجعية إطار الخدمات المصرفية المفتوحة.",
    en: "Regulatory and banking publications, and open banking framework references.",
  },
  "data.source.monshaat.name": { ar: "منشآت", en: "Monsha'at" },
  "data.source.monshaat.body": {
    ar: "تقارير قطاع المنشآت الصغيرة والمتوسطة، وبيانات برامج الدعم والنمو.",
    en: "SME sector reports, and growth and support program data.",
  },
  "data.source.gastat.name": { ar: "الهيئة العامة للإحصاء", en: "General Authority for Statistics (GASTAT)" },
  "data.source.gastat.body": {
    ar: "إحصاءات قطاعية وإقليمية، سوق العمل وأعداد المنشآت.",
    en: "Sector and district level statistics, labor market and business counts.",
  },
  "data.source.more.name": { ar: "مصادر إضافية", en: "More sources" },
  "data.source.more.body": {
    ar: "يتواصل التوسّع في مصادر البيانات الرسمية بعد الإطلاق.",
    en: "Additional official sources are being added as the corpus grows.",
  },
  "data.retrieval.title": { ar: "كيف يعمل الاسترجاع", en: "How retrieval works" },
  "data.retrieval.subtitle": {
    ar: "لا يُدرَّب أي نموذج على هذه البيانات. يُسترجع المحتوى ذو الصلة عند كل طلب ويُستشهد به.",
    en: "No model is trained on this data. Relevant content is retrieved on each request and cited.",
  },
  "data.retrieval.step.query": { ar: "الاستعلام", en: "Query" },
  "data.retrieval.step.embed": { ar: "التمثيل الرقمي", en: "Embed" },
  "data.retrieval.step.retrieve": { ar: "استرجاع أعلى النتائج", en: "Retrieve top matches" },
  "data.retrieval.step.cite": { ar: "استنتاج سوقي موثَّق", en: "Cited market verdict" },
  "data.honesty.title": { ar: "ملاحظة حول التغطية الحالية", en: "A note on current coverage" },
  "data.honesty.body": {
    ar: "لم يتم إدراج مجموعة البيانات بعد؛ استرجاع السوق غير مفعّل في هذه النسخة التجريبية. الأرقام والتغطية أعلاه توضيحية للبنية فقط، وستُستبدل بتغطية فعلية بعد الإدراج.",
    en: "The corpus hasn't been ingested yet; market retrieval isn't live in this demo build. The figures and coverage above are illustrative of the structure only, and will be replaced with real coverage once ingestion is complete.",
  },

  // --- common / auth ---
  "common.nav.home": { ar: "الرئيسية", en: "Home" },
  "common.back.dashboard": { ar: "العودة إلى لوحة الطلبات", en: "Back to dashboard" },
  "common.back.queue": { ar: "العودة إلى قائمة الطلبات", en: "Back to queue" },
  "common.theme.toLight": { ar: "التبديل إلى الوضع الفاتح", en: "Switch to light mode" },
  "common.theme.toDark": { ar: "التبديل إلى الوضع الداكن", en: "Switch to dark mode" },
  "common.loading": { ar: "جارٍ التحميل", en: "Loading" },
  "auth.signOut": { ar: "تسجيل الخروج", en: "Sign out" },
  "auth.workingEllipsis": { ar: "جارٍ العمل…", en: "Working…" },
  "auth.genericError": { ar: "حدث خطأ ما. حاول مرة أخرى.", en: "Something went wrong. Try again." },
  "auth.roleSme": { ar: "صاحب منشأة", en: "Business owner" },
  "auth.roleBank": { ar: "موظف بنك", en: "Bank officer" },

  // --- login ---
  "login.heroHeadline": {
    ar: "دراسة جدوى حيّة\nلكل طلب تمويل",
    en: "A living feasibility study for every financing application.",
  },
  // REVIEW: fintech/regulatory phrasing — confirm with a native reviewer.
  "login.demoNote": {
    ar: "بيئة تجريبية · على غرار إطار الخدمات المصرفية المفتوحة من ساما",
    en: "Demo environment · modeled on SAMA's open banking framework",
  },
  "login.signInTitle": { ar: "تسجيل الدخول", en: "Sign in" },
  "login.signUpTitle": { ar: "إنشاء حسابك", en: "Create your account" },
  "login.signInSubtitle": { ar: "ستُفتح بوابتك بحسب دورك.", en: "Your portal opens based on your role." },
  "login.signUpSubtitle": {
    ar: "أخبرنا في أي جانب أنت وكيف يمكننا التواصل معك.",
    en: "Tell us which side you're on and how to reach you.",
  },
  "login.signingUpAs": { ar: "أسجّل بصفتي", en: "I'm signing up as" },
  "login.email": { ar: "البريد الإلكتروني", en: "Email" },
  "login.password": { ar: "كلمة المرور", en: "Password" },
  "login.emailPlaceholder": { ar: "name@company.sa", en: "name@company.sa" },
  "login.showPassword": { ar: "إظهار كلمة المرور", en: "Show password" },
  "login.hidePassword": { ar: "إخفاء كلمة المرور", en: "Hide password" },
  "login.signInCta": { ar: "تسجيل الدخول", en: "Sign in" },
  "login.createAccountCta": { ar: "إنشاء حساب", en: "Create account" },
  "login.newSme": { ar: "منشأة جديدة؟", en: "New SME?" },
  "login.createAnAccount": { ar: "إنشاء حساب", en: "Create an account" },
  "login.alreadyHaveAccount": { ar: "لديك حساب بالفعل؟", en: "Already have an account?" },
  "login.signInLink": { ar: "تسجيل الدخول", en: "Sign in" },

  // --- SME portal shell ---
  "sme.portalLabel": { ar: "بوابة المنشآت", en: "Business portal" },
  "sme.nav.dashboard": { ar: "لوحة الطلبات", en: "Dashboard" },
  "sme.nav.settings": { ar: "الإعدادات", en: "Settings" },

  // --- SME applications dashboard (SmeDashboardPage, GET /applications) ---
  "sme.dashboard.title": { ar: "طلبات التمويل الخاصة بي", en: "My loan applications" },
  "sme.dashboard.subtitle": {
    ar: "تتبع حالة طلبات التمويل التي قدّمتها.",
    en: "Track the status of your financing applications.",
  },
  "sme.dashboard.createApplication": { ar: "إنشاء طلب جديد", en: "Create application" },
  "sme.dashboard.colCreated": { ar: "تاريخ الإنشاء", en: "Created" },
  "sme.dashboard.colDocuments": { ar: "المستندات", en: "Documents" },
  "sme.dashboard.colStatus": { ar: "الحالة", en: "Status" },
  "sme.dashboard.loading": { ar: "جارٍ تحميل الطلبات…", en: "Loading applications…" },
  "sme.dashboard.loadError": { ar: "تعذّر تحميل الطلبات. حاول مرة أخرى.", en: "Couldn't load applications. Try again." },
  "sme.dashboard.retry": { ar: "إعادة المحاولة", en: "Retry" },
  "sme.dashboard.emptyTitle": { ar: "ابدأ طلبك الأول", en: "Start your first application" },
  "sme.dashboard.emptyBody": {
    ar: "ارفع فواتيرك وكشوفاتك بالعربية أو الإنجليزية. جدوى تنظّم الباقي.",
    en: "Upload your invoices and statements in Arabic or English. Jadwa organizes the rest.",
  },
  "sme.dashboard.status.draft": { ar: "مسودة", en: "Draft" },
  "sme.dashboard.status.processing": { ar: "قيد المعالجة", en: "Processing" },
  "sme.dashboard.status.review_ready": { ar: "جاهز للمراجعة", en: "Ready for review" },
  "sme.dashboard.status.approved": { ar: "مُوافَق عليه", en: "Approved" },
  "sme.dashboard.status.rejected": { ar: "مرفوض", en: "Rejected" },
  "sme.dashboard.status.more_info_needed": { ar: "بحاجة لمعلومات إضافية", en: "More info needed" },
  "sme.dashboard.metric.active": { ar: "طلبات نشطة", en: "Active" },
  "sme.dashboard.metric.inReview": { ar: "قيد المراجعة", en: "In review" },
  "sme.dashboard.metric.approved": { ar: "معتمدة", en: "Approved" },
  "sme.dashboard.metric.totalRequested": { ar: "إجمالي المطلوب", en: "Total requested" },
  "sme.dashboard.metric.totalPending": { ar: "غير متاح بعد", en: "Not available yet" },
  "sme.dashboard.amountNotSet": { ar: "لم يُحدَّد بعد", en: "Not set yet" },
  "sme.dashboard.cardTitle": { ar: "طلب تمويل", en: "Financing application" },
  "sme.dashboard.action.continue": { ar: "متابعة", en: "Continue" },
  "sme.dashboard.action.viewProgress": { ar: "عرض التقدم", en: "View progress" },
  "sme.dashboard.action.reviewAndSubmit": { ar: "مراجعة وإرسال", en: "Review and submit" },
  "sme.dashboard.action.view": { ar: "عرض", en: "View" },

  // --- SME create-application flow (NewApplicationPage, POST /applications) ---
  // Copy matches design-mocks/jadwa_sme_screens.html "New application" exactly.
  // POST /applications now sends amount, term_months, purpose, description.
  "sme.new.title": { ar: "طلب تمويل جديد", en: "New financing application" },
  "sme.new.subtitle": {
    ar: "ابدأ بتفاصيل التمويل، ثم أضِف مستنداتك.",
    en: "Start with the financing details, then add your documents.",
  },
  "sme.new.step.details": { ar: "التفاصيل", en: "Details" },
  "sme.new.step.documents": { ar: "المستندات", en: "Documents" },
  "sme.new.step.review": { ar: "المراجعة", en: "Review" },
  "sme.new.step.submit": { ar: "الإرسال", en: "Submit" },
  "sme.new.formTitle": { ar: "تفاصيل التمويل", en: "Financing details" },
  "sme.new.formLead": {
    ar: "هذه التفاصيل تساعد البنك على تقييم طلبك بدقّة.",
    en: "These details help the bank assess your request accurately.",
  },
  "sme.new.businessFallbackName": { ar: "منشأتك", en: "Your business" },
  "sme.new.businessMetaPending": {
    ar: "تفاصيل ملف المنشأة قيد الربط مع الخادم.",
    en: "Business profile details are pending backend integration.",
  },
  "sme.new.editProfile": { ar: "تعديل الملف", en: "Edit profile" },
  "sme.new.amountLabel": { ar: "المبلغ المطلوب", en: "Amount requested" },
  "sme.new.termLabel": { ar: "مدة التمويل", en: "Financing term" },
  "sme.new.term.6": { ar: "6 أشهر", en: "6 months" },
  "sme.new.term.12": { ar: "12 شهرًا", en: "12 months" },
  "sme.new.term.24": { ar: "24 شهرًا", en: "24 months" },
  "sme.new.term.36": { ar: "36 شهرًا", en: "36 months" },
  "sme.new.purposeLabel": { ar: "الغرض من التمويل", en: "Purpose of financing" },
  "sme.new.purpose.workingCapital": { ar: "رأس مال عامل", en: "Working capital" },
  "sme.new.purpose.equipment": { ar: "شراء معدات", en: "Equipment purchase" },
  "sme.new.purpose.inventory": { ar: "تمويل مخزون", en: "Inventory" },
  "sme.new.purpose.expansion": { ar: "توسعة", en: "Expansion" },
  "sme.new.purpose.other": { ar: "غير ذلك", en: "Other" },
  "sme.new.descriptionLabel": { ar: "وصف مختصر (اختياري)", en: "Short description (optional)" },
  "sme.new.descriptionPlaceholder": {
    ar: "اشرح باختصار كيف سيُستخدم التمويل",
    en: "Briefly explain how the financing will be used",
  },
  "sme.new.submit": { ar: "أنشئ وتابِع إلى المستندات", en: "Create and continue to documents" },
  "sme.new.submitting": { ar: "جارٍ الإنشاء…", en: "Creating…" },
  "sme.new.error": { ar: "تعذّر إنشاء الطلب. حاول مرة أخرى.", en: "Couldn't create the application. Try again." },
  "sme.new.cancel": { ar: "إلغاء", en: "Cancel" },
  "sme.new.whatsNextTitle": { ar: "ماذا يحدث بعد ذلك؟", en: "What happens next?" },
  "sme.new.whatsNext1": {
    ar: "ارفع فواتيرك وكشوفك بأي صيغة.",
    en: "Upload your invoices and statements in any format.",
  },
  "sme.new.whatsNext2": {
    ar: "تقرأ جدوى المستندات وتنظّمها تلقائيًا.",
    en: "Jadwa reads and organizes your documents automatically.",
  },
  "sme.new.whatsNext3": {
    ar: "راجِع الأرقام وصحّح أي خطأ قبل الإرسال.",
    en: "Review the figures and fix anything before you submit.",
  },
  "sme.new.whatsNext4": {
    ar: "أرسِل طلبك الجاهز إلى قائمة البنك.",
    en: "Send your ready application to the bank queue.",
  },

  // --- SME application detail spine (ApplicationDetailPage) ---
  "sme.detail.applicationLabel": { ar: "الطلب", en: "Application" },
  "sme.detail.loading": { ar: "جارٍ تحميل الطلب…", en: "Loading application…" },
  "sme.detail.loadError": { ar: "تعذّر تحميل الطلب. حاول مرة أخرى.", en: "Couldn't load the application. Try again." },
  "sme.detail.retry": { ar: "إعادة المحاولة", en: "Retry" },
  "sme.detail.notFound": { ar: "لم يتم العثور على هذا الطلب.", en: "This application couldn't be found." },
  "sme.detail.existingDocsNote": {
    ar: "{{count}} مستند مرفوع مسبقًا.",
    en: "{{count}} document(s) already uploaded.",
  },
  "sme.detail.analyzeButton": { ar: "تحليل المستندات", en: "Analyze documents" },
  "sme.detail.analyzeStarting": { ar: "جارٍ البدء…", en: "Starting…" },
  "sme.detail.analyzeNeedsDocs": {
    ar: "ارفع مستندًا واحدًا على الأقل قبل التحليل.",
    en: "Upload at least one document before analyzing.",
  },
  "sme.detail.analyzeError": { ar: "تعذّر بدء التحليل. حاول مرة أخرى.", en: "Couldn't start analysis. Try again." },
  "sme.detail.processingTitle": { ar: "جارٍ تحليل مستنداتك", en: "Analyzing your documents" },
  "sme.detail.processingHint": {
    ar: "يستغرق هذا عادةً دقيقة أو دقيقتين. يمكنك البقاء في هذه الصفحة أو العودة لاحقًا.",
    en: "This usually takes a minute or two. Stay on this page or check back later.",
  },
  "sme.detail.stageProgress": { ar: "اكتملت {{done}} من {{total}} مراحل", en: "{{done}} of {{total}} stages complete" },
  "sme.detail.analysisCompleteNotice": {
    ar: "اكتمل التحليل. راجع البيانات المستخرجة أدناه ثم أرسل الطلب.",
    en: "Analysis complete. Review the extracted data below, then submit.",
  },
  "sme.detail.lockedNote": {
    ar: "طلبك مُقفل أمام أي تعديلات إضافية.",
    en: "Your application is locked from further edits.",
  },
  "sme.detail.submitButton": { ar: "إرسال الطلب", en: "Submit application" },
  "sme.detail.submitting": { ar: "جارٍ الإرسال…", en: "Submitting…" },
  "sme.detail.submitError": { ar: "تعذّر إرسال الطلب. حاول مرة أخرى.", en: "Couldn't submit the application. Try again." },
  "sme.detail.summaryTitle": { ar: "ملخص الوضع المالي لمنشأتك", en: "Business health summary" },
  "sme.detail.strengthenTitle": { ar: "نقاط يمكن تعزيزها", en: "Areas to strengthen" },
  "sme.detail.summaryUnavailable": {
    ar: "تعذّر تحميل ملخص الوضع المالي الآن.",
    en: "The business summary isn't available right now.",
  },
  "sme.detail.pdfButton": { ar: "تحميل PDF", en: "Download PDF" },
  "sme.detail.pdfComingSoon": { ar: "قريبًا", en: "Coming soon" },

  // --- SME settings (/sme/settings) — matches design-mocks/jadwa_sme_settings.html ---
  "sme.settings.title": { ar: "الملف والإعدادات", en: "Profile and settings" },
  "sme.settings.subtitle": {
    ar: "راجِع بيانات منشأتك وحدّثها، وأدِر حسابك وتفضيلاتك.",
    en: "Review and update your business details, and manage your account and preferences.",
  },
  "sme.settings.nav.business": { ar: "ملف المنشأة", en: "Business profile" },
  "sme.settings.nav.account": { ar: "الحساب", en: "Account" },
  "sme.settings.nav.prefs": { ar: "التفضيلات", en: "Preferences" },

  // Business profile — wired to GET/PATCH /api/v1/me/profile; cr_number is read-only.
  "sme.settings.biz.title": { ar: "ملف المنشأة", en: "Business profile" },
  "sme.settings.biz.lead": {
    ar: "هذه البيانات تظهر للبنك مع كل طلب تمويل.",
    en: "These details are shown to the bank with every financing application.",
  },
  "sme.settings.biz.pendingNote": {
    ar: "قراءة ملف المنشأة وحفظه قيد الربط مع الخادم.",
    en: "Reading and saving your business profile is pending backend integration.",
  },
  "sme.settings.biz.nameLabel": { ar: "اسم المنشأة", en: "Business name" },
  "sme.settings.biz.crLabel": { ar: "رقم السجل التجاري", en: "Commercial registration number" },
  "sme.settings.biz.crHint": {
    ar: "يُستخدم لمطابقة سجلّك البنكي، غيّره بحذر.",
    en: "Used to match your bank ledger. Change with care.",
  },
  "sme.settings.biz.yearLabel": { ar: "سنة التأسيس", en: "Established year" },
  "sme.settings.biz.sectorLabel": { ar: "القطاع", en: "Sector" },
  "sme.settings.biz.sector.logistics": { ar: "لوجستيات", en: "Logistics" },
  "sme.settings.biz.sector.foodBeverage": { ar: "أغذية ومشروبات", en: "Food and beverage" },
  "sme.settings.biz.sector.construction": { ar: "إنشاءات", en: "Construction" },
  "sme.settings.biz.sector.retail": { ar: "تجزئة", en: "Retail" },
  "sme.settings.biz.sector.manufacturing": { ar: "تصنيع", en: "Manufacturing" },
  "sme.settings.biz.districtLabel": { ar: "المدينة أو الحي", en: "District or city" },
  "sme.settings.biz.descriptionLabel": { ar: "وصف المنشأة", en: "Business description" },
  "sme.settings.biz.descriptionPlaceholder": {
    ar: "نبذة قصيرة عن نشاط منشأتك",
    en: "A short note about what your business does",
  },
  "sme.settings.biz.save": { ar: "حفظ التغييرات", en: "Save changes" },
  "sme.settings.biz.saving": { ar: "جارٍ الحفظ…", en: "Saving…" },
  "sme.settings.biz.saved": { ar: "تم حفظ التغييرات.", en: "Changes saved." },
  "sme.settings.biz.saveError": { ar: "تعذّر الحفظ. حاول مرة أخرى.", en: "Could not save. Try again." },
  "sme.settings.biz.loadError": {
    ar: "تعذّر تحميل ملف المنشأة. حاول مرة أخرى.",
    en: "Could not load your business profile. Try again.",
  },
  "sme.settings.biz.crReadOnly": {
    ar: "لا يمكن تعديله — يُستخدم لمطابقة الكشف البنكي.",
    en: "Cannot be changed — used to match your bank ledger.",
  },
  "sme.settings.biz.loadingProfile": { ar: "جارٍ تحميل ملف المنشأة…", en: "Loading your business profile…" },
  "sme.settings.biz.cancel": { ar: "إلغاء", en: "Cancel" },

  // Account — email is real (Supabase session); password change is real too
  // (supabase.auth.updateUser, straightforward with an existing session, no
  // current-password re-check needed).
  "sme.settings.account.title": { ar: "الحساب", en: "Account" },
  "sme.settings.account.lead": { ar: "بيانات الدخول والأمان.", en: "Your sign in and security details." },
  "sme.settings.account.emailLabel": { ar: "البريد الإلكتروني", en: "Email" },
  "sme.settings.account.emailHint": { ar: "يُستخدم لتسجيل الدخول.", en: "Used to sign in." },
  "sme.settings.account.newPasswordLabel": { ar: "كلمة مرور جديدة", en: "New password" },
  "sme.settings.account.confirmPasswordLabel": { ar: "تأكيد كلمة المرور", en: "Confirm password" },
  "sme.settings.account.update": { ar: "تحديث الحساب", en: "Update account" },
  "sme.settings.account.updating": { ar: "جارٍ التحديث…", en: "Updating…" },
  "sme.settings.account.updated": { ar: "تم تحديث كلمة المرور.", en: "Password updated." },
  "sme.settings.account.mismatch": { ar: "كلمتا المرور غير متطابقتين.", en: "Passwords don't match." },
  "sme.settings.account.tooShort": {
    ar: "كلمة المرور قصيرة جدًا (6 أحرف على الأقل).",
    en: "Password is too short (at least 6 characters).",
  },

  // Preferences — language + theme are real (existing LangProvider/ThemeProvider
  // state, applied immediately); notification switches are local only, per the
  // product having no notification system yet.
  "sme.settings.prefs.title": { ar: "التفضيلات", en: "Preferences" },
  "sme.settings.prefs.lead": { ar: "اللغة والمظهر والإشعارات.", en: "Language, appearance, and notifications." },
  "sme.settings.prefs.languageLabel": { ar: "اللغة", en: "Language" },
  "sme.settings.prefs.languageHint": { ar: "لغة الواجهة الافتراضية", en: "Default interface language" },
  "sme.settings.prefs.languageArabic": { ar: "العربية", en: "Arabic" },
  "sme.settings.prefs.languageEnglish": { ar: "الإنجليزية", en: "English" },
  "sme.settings.prefs.appearanceLabel": { ar: "المظهر", en: "Appearance" },
  "sme.settings.prefs.appearanceHint": { ar: "فاتح أو داكن", en: "Light or dark" },
  "sme.settings.prefs.appearanceLight": { ar: "فاتح", en: "Light" },
  "sme.settings.prefs.appearanceDark": { ar: "داكن", en: "Dark" },
  "sme.settings.prefs.notifStatusLabel": { ar: "تحديثات حالة الطلب", en: "Application status updates" },
  "sme.settings.prefs.notifStatusHint": {
    ar: "إشعار عند تغيّر حالة أي طلب",
    en: "Notify me when an application status changes",
  },
  "sme.settings.prefs.notifDecisionLabel": { ar: "قرارات البنك", en: "Bank decisions" },
  "sme.settings.prefs.notifDecisionHint": {
    ar: "إشعار عند موافقة أو رفض أو طلب معلومات",
    en: "Notify me on approve, reject, or request for info",
  },

  // --- SME home ---
  "sme.home.welcome": { ar: "مرحبًا محمد", en: "Welcome, Mohammed" },
  "sme.home.appStatus": {
    ar: "طلب التمويل رقم {{ref}} قيد المعالجة الآن.",
    en: "Financing application {{ref}} is being processed now.",
  },
  "sme.home.stagesTitle": { ar: "مراحل دراسة الجدوى", en: "Feasibility study stages" },
  "sme.home.stagesBadge": { ar: "قيد المعالجة", en: "In progress" },
  "sme.home.stagesAriaLabel": { ar: "تقدّم المعالجة عبر ست مراحل", en: "Progress across six stages" },
  "sme.home.stage.extract": { ar: "الاستخراج", en: "Extract" },
  "sme.home.stage.forensic": { ar: "التدقيق", en: "Forensic" },
  "sme.home.stage.stressTest": { ar: "اختبار الضغط", en: "Stress test" },
  "sme.home.stage.market": { ar: "السوق", en: "Market" },
  "sme.home.stage.riskModel": { ar: "المخاطر", en: "Risk model" },
  "sme.home.stage.record": { ar: "السجل", en: "Record" },
  "sme.home.documentsTitle": { ar: "المستندات", en: "Documents" },
  "sme.home.doc.fuelInvoice": { ar: "فاتورة وقود أكتوبر", en: "October fuel invoice" },
  "sme.home.doc.zatcaReceipt": { ar: "إيصال ZATCA", en: "ZATCA receipt" },
  "sme.home.doc.warehouseLease": { ar: "عقد إيجار المستودع", en: "Warehouse lease agreement" },
  "sme.home.doc.matched": { ar: "مطابقة", en: "Matched" },
  "sme.home.reviewLink": { ar: "مراجعة البيانات المستخرجة", en: "Review extracted data" },
  "sme.home.doc.needsReview": { ar: "بحاجة لمراجعتك", en: "Needs your review" },
  "sme.home.tip": {
    ar: "نصيحة قبل الإرسال: 80% من مشترياتك من مورّد واحد. أرفق عقد مورّد بديل لتقوية طلبك.",
    en: "Tip before you submit: 80% of your purchases come from a single supplier. Attach an alternate supplier contract to strengthen your application.",
  },

  // --- document upload ---
  "upload.dropzoneAriaLabel": {
    ar: "أضف مستندات: اسحب الملفات هنا أو اضغط Enter لتصفّح الملفات",
    en: "Add documents: drag files here or press Enter to browse",
  },
  "upload.dropHere": { ar: "اسحب المستندات هنا", en: "Drop documents here" },
  "upload.hint": {
    ar: "فواتير، إيصالات، كشوف بالعربي أو الإنجليزي",
    en: "Invoices, receipts, statements in Arabic or English",
  },
  "upload.browse": { ar: "تصفّح الملفات", en: "Browse files" },
  "upload.errorEmpty": { ar: "هذا الملف فارغ.", en: "This file is empty." },
  "upload.errorTooLarge": { ar: "حجم الملف يتجاوز 15 ميجابايت.", en: "This file is over 15 MB." },
  "upload.errorUnsupportedType": { ar: "نوع الملف غير مدعوم.", en: "Unsupported file type." },
  "upload.errorFailed": { ar: "فشل الرفع. حاول مرة أخرى.", en: "Upload failed. Try again." },
  "upload.retry": { ar: "إعادة المحاولة", en: "Retry" },
  "upload.statusQueued": { ar: "في الانتظار", en: "Queued" },
  "upload.statusUploaded": { ar: "تم الرفع", en: "Uploaded" },
  "upload.statusFailed": { ar: "فشل", en: "Failed" },

  // --- bank dashboard shell / queue --- (design-mocks/jadwa_bank_screens.html "Queue")
  "bank.dashboardLabel": { ar: "لوحة تحكم البنك", en: "Bank dashboard" },
  "bank.nav.queue": { ar: "قائمة الطلبات", en: "Application queue" },
  "bank.queue.subtitle": {
    ar: "الطلبات المُقدَّمة، مُقيَّمة مسبقًا، الأحدث أولاً.",
    en: "Submitted applications, pre scored, newest first.",
  },
  "bank.queue.filterSubmitted": { ar: "مُقدَّم", en: "Submitted" },
  "bank.queue.filterTooltip": {
    ar: "متاح عندما تتوفر طلبات في القائمة",
    en: "Available once applications are in the queue",
  },
  "bank.queue.kpi.inQueue": { ar: "في القائمة", en: "In queue" },
  "bank.queue.kpi.flagged": { ar: "أعلام حمراء", en: "Flagged" },
  "bank.queue.kpi.needsReview": { ar: "بحاجة لمراجعة", en: "Needs review" },
  "bank.queue.kpi.avgScore": { ar: "متوسط الدرجة", en: "Average score" },
  "bank.queue.kpi.scorePending": { ar: "غير متاح", en: "Not available" },
  "bank.queue.colBusiness": { ar: "المنشأة", en: "Business" },
  "bank.queue.colSector": { ar: "القطاع", en: "Sector" },
  "bank.queue.colSubmitted": { ar: "تاريخ الإرسال", en: "Submitted" },
  "bank.queue.colForensic": { ar: "التدقيق", en: "Forensic" },
  "bank.queue.colAmount": { ar: "المبلغ", en: "Amount" },
  "bank.queue.colScore": { ar: "الدرجة", en: "Score" },
  "bank.queue.amountPendingTooltip": {
    ar: "بيانات المبلغ غير متاحة بعد",
    en: "Amount data isn't available yet",
  },
  "bank.queue.loading": { ar: "جارٍ تحميل القائمة…", en: "Loading the queue…" },
  "bank.queue.loadError": { ar: "تعذّر تحميل القائمة. حاول مرة أخرى.", en: "Couldn't load the queue. Try again." },
  "bank.queue.retry": { ar: "إعادة المحاولة", en: "Retry" },
  "bank.queue.emptyTitle": { ar: "لا توجد طلبات في القائمة", en: "No applications in the queue" },
  "bank.queue.emptyBody": {
    ar: "الطلبات المُقدَّمة ستظهر هنا، مُقيَّمة مسبقًا.",
    en: "Submitted applications land here, pre scored.",
  },

  // --- bank application detail --- (design-mocks/jadwa_bank_screens.html "Application detail")
  // REVIEW: "underwriting desk" — banking-domain term, confirm preferred AR phrasing.
  "bank.detail.deskLabel": { ar: "مكتب التحليل الائتماني", en: "Underwriting desk" },
  "bank.detail.subtitleNoCr": { ar: "{{sector}} · {{district}}", en: "{{sector}} · {{district}}" },
  "bank.detail.crLabel": { ar: "السجل التجاري", en: "CR" },
  "bank.detail.submittedLabel": { ar: "أُرسل", en: "Submitted" },
  "bank.detail.amountLabel": { ar: "المبلغ", en: "Amount" },
  "bank.detail.amountPending": { ar: "غير متاح بعد", en: "Not available yet" },
  "bank.detail.amountSar": { ar: "ر.س", en: "SAR" },
  "bank.detail.metric.reconciled": { ar: "المطابقة", en: "Reconciled" },
  "bank.detail.metric.businessModel": { ar: "نموذج العمل", en: "Business model" },
  "bank.detail.metric.documents": { ar: "المستندات", en: "Documents" },
  "bank.detail.metric.forensic": { ar: "التدقيق الجنائي", en: "Forensic" },
  "bank.detail.notComputedShort": { ar: "لم يُحتسب", en: "Not computed" },
  "bank.detail.rail.title": { ar: "ملخص القرار", en: "Decision summary" },
  "bank.detail.marketTitle": { ar: "حكم السوق", en: "Market verdict" },
  "bank.detail.marketBody": {
    ar: "سياق السوق السعودي المستند إلى بيانات ساما ومنشآت.",
    en: "Saudi market context grounded in SAMA and Monsha'at data.",
  },
  // Market verdict card — data comes from MarketVerdict shape (types.ts). Language rule:
  // "grounded in / cites its source" — never "trained on" (it's RAG retrieval).
  "bank.detail.market.trendLabel": { ar: "اتجاه القطاع", en: "Sector trend" },
  "bank.detail.market.trend.growing": { ar: "نامٍ", en: "Growing" },
  "bank.detail.market.trend.stable": { ar: "مستقر", en: "Stable" },
  "bank.detail.market.trend.declining": { ar: "متراجع", en: "Declining" },
  "bank.detail.market.saturationLabel": { ar: "كثافة المنطقة", en: "District saturation" },
  "bank.detail.market.saturation.low": { ar: "منخفضة", en: "Low" },
  "bank.detail.market.saturation.medium": { ar: "متوسطة", en: "Medium" },
  "bank.detail.market.saturation.high": { ar: "مرتفعة", en: "High" },
  "bank.detail.market.insightLabel": { ar: "الاستنتاج السوقي", en: "Market insight" },
  "bank.detail.market.sourcesLabel": { ar: "المصادر المُستشهَد بها", en: "Sources cited" },
  "bank.detail.market.groundedNote": {
    ar: "مستند إلى بيانات سعودية رسمية · يُستشهد بكل استنتاج بمصدره",
    en: "Grounded in official Saudi data · every insight cites its source",
  },
  "bank.detail.market.noData": {
    ar: "الاستنتاج السوقي غير متاح — لم يعمل المستشار بعد على هذا الطلب.",
    en: "Market verdict unavailable — Oracle has not yet run for this application.",
  },

  "bank.detail.sandboxTitle": { ar: "مِنصّة المخاطر التفاعلية", en: "Risk sandbox" },
  "bank.detail.sandboxBody": {
    ar: "حرّك عوامل السيناريو وشاهد المخاطر تُحسب حيًّا.",
    en: "Move scenario levers and watch the risk recalculate live.",
  },
  "bank.detail.comingSoon": { ar: "قريبًا", en: "Coming soon" },
  "bank.detail.phase4": { ar: "المرحلة الرابعة", en: "Phase 4" },
  "bank.detail.documentsEmpty": { ar: "لا توجد مستندات مستخرجة بعد.", en: "No extracted documents yet." },

  "bank.detail.matchHighConfidence": { ar: "ثقة عالية", en: "High confidence" },
  "bank.detail.matchLowConfidence": { ar: "ثقة منخفضة", en: "Low confidence" },
  "bank.detail.approve": { ar: "الموافقة", en: "Approve" },
  "bank.detail.requestInfo": { ar: "طلب معلومات", en: "Request info" },
  "bank.detail.reject": { ar: "الرفض", en: "Reject" },
  "bank.detail.deciding": { ar: "جارٍ الإرسال…", en: "Submitting…" },
  "bank.detail.decisionError": {
    ar: "تعذّر تسجيل القرار. حاول مرة أخرى.",
    en: "Couldn't record the decision. Try again.",
  },
  "bank.detail.noteLabel": { ar: "ملاحظة للمنشأة", en: "Note to the SME" },
  "bank.detail.notePlaceholder": {
    ar: "ما المعلومات الإضافية المطلوبة؟",
    en: "What additional information do you need?",
  },
  "bank.detail.sendRequest": { ar: "إرسال الطلب", en: "Send request" },
  "bank.detail.decisionRecorded": { ar: "تم تسجيل القرار.", en: "Decision recorded." },
  "bank.detail.notYetSubmitted": { ar: "لم يُقدَّم للمراجعة بعد.", en: "Not yet submitted for review." },
  "bank.detail.signOff": {
    ar: "تم التحقق من كل رقم بواسطة جدوى",
    en: "Every figure cross checked by Jadwa",
  },

  // --- forensic report card (ForensicReportCard, mirrors ForensicReport in models.py) ---
  "forensic.title": { ar: "التدقيق المالي", en: "Financial audit" },
  "forensic.status.green": { ar: "مطابقة", en: "Reconciled" },
  "forensic.status.yellow": { ar: "بحاجة لمراجعة", en: "Review needed" },
  "forensic.status.red": { ar: "مخالفات مرصودة", en: "Discrepancies flagged" },
  "forensic.reconciledLabel": { ar: "نسبة المطابقة", en: "Reconciled" },
  "forensic.emptyState": { ar: "لا توجد مخالفات", en: "No discrepancies found" },
  "forensic.severity.high": { ar: "مرتفعة", en: "High" },
  "forensic.severity.medium": { ar: "متوسطة", en: "Medium" },
  "forensic.severity.low": { ar: "منخفضة", en: "Low" },
  "forensic.loading": { ar: "جارٍ تحميل التقرير...", en: "Loading report..." },
  "forensic.loadError": { ar: "تعذّر تحميل تقرير التدقيق.", en: "Couldn't load the forensic report." },
  "forensic.retry": { ar: "إعادة المحاولة", en: "Retry" },
  "forensic.notComputed": {
    ar: "لم يكتمل التحليل المالي لهذا الطلب بعد.",
    en: "The forensic analysis for this application hasn't run yet.",
  },

  // --- SME review screen (ReviewDocumentsPage) ---
  "review.title": { ar: "راجع بيانات المستندات", en: "Review extracted data" },
  "review.subtitle": {
    ar: "تحقق من البيانات التي استخرجها الذكاء الاصطناعي من مستنداتك، وصحّح أي خطأ قبل المتابعة.",
    en: "Check what the AI extracted from your documents and correct anything that's wrong before continuing.",
  },
  "review.loading": { ar: "جارٍ تحميل المستندات…", en: "Loading documents…" },
  "review.loadError": { ar: "تعذّر تحميل المستندات. حاول مرة أخرى.", en: "Couldn't load documents. Try again." },
  "review.retry": { ar: "إعادة المحاولة", en: "Retry" },
  "review.empty": { ar: "لا توجد مستندات مستخرجة بعد.", en: "No extracted documents yet." },
  "review.lowConfidence": { ar: "ثقة منخفضة، تحقق منها", en: "Low confidence, double check" },
  "review.confirmed": { ar: "مؤكَّد", en: "Confirmed" },
  "review.needsConfirmation": { ar: "بانتظار تأكيدك", en: "Awaiting your confirmation" },
  "review.field.vendor": { ar: "المورّد", en: "Vendor" },
  "review.field.amount": { ar: "المبلغ", en: "Amount" },
  "review.field.date": { ar: "التاريخ", en: "Date" },
  "review.field.type": { ar: "نوع المستند", en: "Document type" },
  "review.type.zatca_receipt": { ar: "إيصال ZATCA", en: "ZATCA receipt" },
  "review.type.invoice": { ar: "فاتورة", en: "Invoice" },
  "review.type.bank_statement": { ar: "كشف حساب بنكي", en: "Bank statement" },
  "review.type.contract": { ar: "عقد", en: "Contract" },
  "review.type.other": { ar: "أخرى", en: "Other" },
  "review.edit": { ar: "تعديل", en: "Edit" },
  "review.save": { ar: "حفظ", en: "Save" },
  "review.cancel": { ar: "إلغاء", en: "Cancel" },
  "review.confirm": { ar: "تأكيد صحة البيانات", en: "Confirm this is correct" },
  "review.saveError": { ar: "تعذّر حفظ التعديل. حاول مرة أخرى.", en: "Couldn't save the correction. Try again." },
  "review.saving": { ar: "جارٍ الحفظ…", en: "Saving…" },
  "review.allConfirmedTitle": { ar: "تم تأكيد جميع المستندات", en: "All documents confirmed" },
  "review.progress": { ar: "تم تأكيد {{done}} من {{total}}", en: "{{done}} of {{total}} confirmed" },
  "review.continue": { ar: "متابعة", en: "Continue" },
  "review.amountValidation": { ar: "أدخل مبلغًا صحيحًا أكبر من صفر.", en: "Enter a valid amount greater than zero." },


  // --- weakness report card (WeaknessReportCard, mirrors WeaknessReport in models.py) ---
  "weakness.title": { ar: "تقرير نقاط الضعف", en: "Weakness report" },
  // UI cue derived from business_model_score — not a ForensicStatus verdict.
  "weakness.edge.pass": { ar: "نموذج عمل قوي", en: "Strong business model" },
  "weakness.edge.review": { ar: "بحاجة لمراجعة", en: "Needs review" },
  "weakness.edge.flag": { ar: "نموذج عمل ضعيف", en: "Weak business model" },
  "weakness.scoreLabel": { ar: "درجة نموذج العمل", en: "Business model score" },
  "weakness.emptyState": { ar: "لا توجد نقاط ضعف جوهرية", en: "No critical weaknesses found" },
  "weakness.mitigationsTitle": { ar: "إجراءات موصى بها", en: "Recommended actions" },
  "weakness.mitigationInlineLabel": { ar: "مقترح:", en: "Suggested:" },
  "weakness.loading": { ar: "جارٍ تحميل تقرير نقاط الضعف...", en: "Loading weakness report..." },
  "weakness.loadError": { ar: "تعذّر تحميل تقرير نقاط الضعف.", en: "Couldn't load the weakness report." },
  "weakness.retry": { ar: "إعادة المحاولة", en: "Retry" },
  "weakness.notComputed": {
    ar: "لم يكتمل تحليل نقاط الضعف لهذا الطلب بعد.",
    en: "The weakness analysis for this application hasn't run yet.",
  },
} as const;

export type StringKey = keyof typeof STRINGS;
