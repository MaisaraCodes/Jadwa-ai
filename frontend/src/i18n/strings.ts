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

  // --- common / auth ---
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
    en: "Demo environment · modeled on SAMA's open-banking framework",
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
  "demo.smeUserName": { ar: "محمد الحربي", en: "Mohammed Al-Harbi" },
  "demo.smeUserInitial": { ar: "م", en: "M" },

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
  "sme.home.doc.fuelInvoice": { ar: "فاتورة وقود — أكتوبر", en: "Fuel invoice — October" },
  "sme.home.doc.zatcaReceipt": { ar: "إيصال ZATCA", en: "ZATCA receipt" },
  "sme.home.doc.warehouseLease": { ar: "عقد إيجار المستودع", en: "Warehouse lease agreement" },
  "sme.home.doc.matched": { ar: "مطابقة", en: "Matched" },
  "sme.home.reviewLink": { ar: "مراجعة البيانات المستخرجة", en: "Review extracted data" },
  "sme.home.doc.needsReview": { ar: "بحاجة لمراجعتك", en: "Needs your review" },
  "sme.home.tip": {
    ar: "نصيحة قبل الإرسال: 80% من مشترياتك من مورّد واحد — أرفق عقد مورّد بديل لتقوية طلبك.",
    en: "Tip before you submit: 80% of your purchases come from a single supplier — attach an alternate supplier contract to strengthen your application.",
  },

  // --- document upload ---
  "upload.dropzoneAriaLabel": {
    ar: "أضف مستندات: اسحب الملفات هنا أو اضغط Enter لتصفّح الملفات",
    en: "Add documents: drag files here or press Enter to browse",
  },
  "upload.dropHere": { ar: "اسحب المستندات هنا", en: "Drop documents here" },
  "upload.hint": {
    ar: "فواتير، إيصالات، كشوف — عربي أو إنجليزي",
    en: "Invoices, receipts, statements — Arabic or English",
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

  // --- bank dashboard shell / queue ---
  "bank.dashboardLabel": { ar: "لوحة تحكم البنك", en: "Bank dashboard" },
  "bank.nav.queue": { ar: "قائمة الطلبات", en: "Application queue" },
  "bank.queue.subtitle": {
    ar: "الطلبات المُقدَّمة، مُقيَّمة مسبقًا، الأحدث أولاً.",
    en: "Submitted applications, pre-scored, newest first.",
  },
  "bank.queue.filterSubmitted": { ar: "مُقدَّم", en: "Submitted" },
  "bank.queue.filterTooltip": {
    ar: "متاح عندما تتوفر طلبات في القائمة",
    en: "Available once applications are in the queue",
  },
  "bank.queue.colBusiness": { ar: "المنشأة", en: "Business" },
  "bank.queue.colSector": { ar: "القطاع", en: "Sector" },
  "bank.queue.colForensic": { ar: "التدقيق", en: "Forensic" },
  "bank.queue.colScore": { ar: "الدرجة", en: "Score" },
  "bank.demo.company": { ar: "شركة رواد اللوجستية", en: "Rawad Logistics" },
  "bank.demo.sector": { ar: "الخدمات اللوجستية · الخرج", en: "Logistics · Al-Kharj" },
  "bank.demo.reviewNeeded": { ar: "بحاجة لمراجعة", en: "Review needed" },

  // --- bank application detail ---
  // REVIEW: "underwriting desk" — banking-domain term, confirm preferred AR phrasing.
  "bank.detail.deskLabel": { ar: "مكتب التحليل الائتماني", en: "Underwriting desk" },
  "demo.bankUserName": { ar: "خالد · بنك الإنماء", en: "Khalid · Alinma" },
  "demo.bankUserInitial": { ar: "خ", en: "K" },
  "bank.detail.subtitle": {
    ar: "الخدمات اللوجستية · الخرج · السجل التجاري {{cr}} · تاريخ التقديم {{date}}",
    en: "Logistics · Al-Kharj · CR {{cr}} · submitted {{date}}",
  },
  "bank.detail.metric.reconciled": { ar: "المطابقة", en: "Reconciled" },
  "bank.detail.metric.businessModel": { ar: "نموذج العمل", en: "Business model" },
  "bank.detail.metric.sectorTrend": { ar: "اتجاه القطاع", en: "Sector trend" },
  "bank.detail.metric.riskClass": { ar: "فئة المخاطر", en: "Risk class" },
  "bank.detail.growing": { ar: "نمو +14%", en: "Growing +14%" },
  "bank.detail.riskMedium": { ar: "متوسطة", en: "Medium" },
  "bank.detail.sandboxTitle": { ar: "بيئة اختبار المخاطر", en: "Risk sandbox" },
  "bank.detail.fuelCostShock": { ar: "صدمة تكلفة الوقود", en: "Fuel cost shock" },
  "bank.detail.monthNov": { ar: "نوفمبر", en: "Nov" },
  "bank.detail.monthOct": { ar: "أكتوبر", en: "Oct" },
  "bank.detail.bufferCaption": {
    ar: "ينخفض الاحتياطي إلى أقل من {{buffer}} شهر في الشهر {{month}} بحسب هذا السيناريو.",
    en: "Buffer dips below {{buffer}} month in month {{month}} under this scenario.",
  },
  "bank.detail.approve": { ar: "الموافقة", en: "Approve" },
  "bank.detail.requestInfo": { ar: "طلب معلومات", en: "Request info" },
  "bank.detail.reject": { ar: "الرفض", en: "Reject" },
  "bank.detail.notWiredTitle": {
    ar: "غير مفعّل بعد — واجهة مراجعة الطلبات ضمن المرحلة الثانية",
    en: "Not wired yet — applications review API is Phase 2",
  },
  "bank.detail.signOff": {
    ar: "تم التحقق من كل رقم بواسطة جدوى",
    en: "Every figure cross-checked by Jadwa",
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
  "review.backLink": { ar: "العودة إلى الرئيسية", en: "Back to home" },
  "review.loading": { ar: "جارٍ تحميل المستندات…", en: "Loading documents…" },
  "review.loadError": { ar: "تعذّر تحميل المستندات. حاول مرة أخرى.", en: "Couldn't load documents. Try again." },
  "review.retry": { ar: "إعادة المحاولة", en: "Retry" },
  "review.empty": { ar: "لا توجد مستندات مستخرجة بعد.", en: "No extracted documents yet." },
  "review.lowConfidence": { ar: "تحقق منها — ثقة منخفضة", en: "Double-check — low confidence" },
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

  // --- bank application detail: tabs ---
  "bank.detail.tab.overview": { ar: "نظرة عامة", en: "Overview" },
  "bank.detail.tab.forensic": { ar: "التدقيق المالي", en: "Financial audit" },
  "bank.detail.tab.weakness": { ar: "نقاط الضعف", en: "Weakness report" },
  "bank.detail.tab.market": { ar: "السوق", en: "Market verdict" },
  "bank.detail.tab.comingSoon": { ar: "قريبًا", en: "Coming soon" },

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
