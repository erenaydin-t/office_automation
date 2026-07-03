<template>
	<div class="oa-panel" :data-theme="theme" dir="rtl" lang="fa">

		<!-- ============ TOP APP BAR ============ -->
		<header data-r="appbar" class="oa-appbar">
			<button data-r="burger" @click="drawerOpen=!drawerOpen" class="oa-iconbtn h-surface1" aria-label="باز/بستن منو"><span class="ico">menu</span></button>
			<div data-r="logowrap" class="oa-logowrap">
				<div class="oa-logo"><span class="ico">mail</span></div>
				<div class="oa-logo-text">
					<span class="oa-logo-fa">اتوماسیون اداری</span>
					<span class="oa-logo-en">Office Automation</span>
				</div>
			</div>
			<div data-r="topsearch" class="oa-topsearch">
				<span class="ico">search</span>
				<input v-model="search" class="oa-searchinput" placeholder="جستجوی نامه، شماره، فرستنده…" aria-label="جستجو" />
			</div>
			<div class="oa-spacer"></div>
			<div data-r="profchip" class="oa-profchip">
				<div class="oa-prof-avatar">{{ meInitials }}</div>
				<div data-r="profmeta" class="oa-profmeta">
					<span class="oa-prof-name">{{ meName }}</span>
					<span class="oa-prof-role">{{ meRole }}</span>
				</div>
			</div>
		</header>

		<div class="oa-body">
			<!-- ============ NAV DRAWER ============ -->
			<nav data-r="drawer" :data-open="drawerOpen ? '1' : '0'" class="oa-drawer">
				<button @click="openCompose()" class="oa-compose-btn h-primary">
					<span class="ico">edit_square</span>ایجاد نامه جدید
				</button>
				<span class="oa-nav-label">منو</span>
				<button v-for="m in menu" :key="m.key" @click="m.go()" class="oa-navbtn h-surface1" :class="{ active: view===m.key }">
					<span class="ico">{{ m.icon }}</span>{{ m.label }}
					<span v-if="m.badge" class="oa-navbtn-badge">{{ faNum(m.badge) }}</span>
				</button>
				<span class="oa-nav-label tight">داده‌های پایه</span>
				<button v-for="m in masters" :key="m.label" @click="m.go()" class="oa-masterbtn h-surface1">
					<span class="ico">{{ m.icon }}</span>{{ m.label }}
				</button>
			</nav>
			<div data-r="navscrim" :data-open="drawerOpen ? '1' : '0'" @click="drawerOpen=false" class="oa-navscrim"></div>

			<!-- ============ MAIN ============ -->
			<main class="oa-main">
				<!-- DASHBOARD -->
				<div v-if="view==='dashboard'" class="oa-dash">
					<div data-r="dashhead" class="oa-dashhead">
						<div>
							<div class="oa-dash-date">{{ todayStr }}</div>
							<h1 class="oa-dash-title">سلام {{ meName }}، خلاصهٔ کارتابل امروز</h1>
						</div>
						<button @click="openCompose()" class="oa-primary-btn h-primary">
							<span class="ico">add</span>نامه جدید
						</button>
					</div>
					<div data-r="grid4" class="oa-grid4">
						<button v-for="c in statCards" :key="c.label" @click="openStat(c)" class="oa-statcard h-bord">
							<div class="oa-statcard-head">
								<span class="oa-statcard-label">{{ c.label }}</span>
								<div class="oa-statcard-icon" :style="{background:c.tintBg}"><span class="ico" :style="{color:c.color}">{{ c.icon }}</span></div>
							</div>
							<div class="oa-statcard-value" :style="{color:c.color}">{{ faNum(c.value) }}</div>
							<div class="oa-statcard-note">{{ c.note }}</div>
						</button>
					</div>

					<div class="oa-section-title">دسترسی سریع</div>
					<div data-r="grid4" class="oa-grid4 tight">
						<button v-for="s in shortcuts" :key="s.label" @click="s.go()" class="oa-shortcut h-bord">
							<div class="oa-shortcut-icon"><span class="ico">{{ s.icon }}</span></div>
							<span class="oa-shortcut-label">{{ s.label }}</span>
							<span v-if="s.count!=null" class="oa-shortcut-count">{{ faNum(s.count) }}</span>
							<span v-else class="ico oa-shortcut-arrow">north_east</span>
						</button>
					</div>

					<div data-r="grid2" class="oa-grid2">
						<div class="oa-card">
							<div class="oa-card-head">
								<span class="oa-card-title">در انتظار اقدام شما</span>
								<button @click="goInbox()" class="oa-link-btn">مشاهده همه</button>
							</div>
							<div v-if="!pending.length" class="oa-empty">موردی نیست.</div>
							<button v-for="row in pending" :key="row.name" @click="openLetter(row.reference_name)" class="oa-listrow h-surface1">
								<div class="oa-avatar oa-avatar-40" :style="{background:avatarColor(row.sender)}">{{ initials(row.sender) }}</div>
								<div class="oa-listrow-main">
									<div class="oa-listrow-title">{{ row.reference_title }}</div>
									<div class="oa-listrow-sub">{{ row.sender }}</div>
								</div>
								<span class="oa-chip oa-chip-ref" :style="refChip(row.referral_type)">{{ faType(row.referral_type) }}</span>
								<span class="oa-time">{{ shortDate(row.creation) }}</span>
							</button>
						</div>
						<div class="oa-col-gap20">
							<div v-for="g in moduleGroups" :key="g.title" class="oa-modcard">
								<div class="oa-modcard-title"><span class="ico">{{ g.icon }}</span>{{ g.title }}</div>
								<button v-for="it in g.items" :key="it.label" @click="it.go()" class="oa-modlink h-surface1"><span class="ico oa-modlink-ico">{{ it.icon }}</span>{{ it.label }}<span class="ico oa-modlink-arrow">north_east</span></button>
							</div>
						</div>
					</div>
				</div>

				<!-- INBOX -->
				<div v-else-if="view==='inbox'" class="oa-inbox">
					<div data-r="folderpane" class="oa-folderpane">
						<div v-for="grp in folderGroups" :key="grp.title" class="oa-foldergroup">
							<div class="oa-foldergroup-title">{{ grp.title }}</div>
							<button v-for="f in grp.items" :key="f.key" @click="selectFolder(f)" class="oa-folderbtn h-surface1" :class="{ active: folder===f.key }">
								<span class="ico">{{ f.icon }}</span>{{ f.label }}
								<span v-if="f.count" class="oa-folderbtn-count">{{ faNum(f.count) }}</span>
							</button>
						</div>
					</div>
					<div class="oa-inbox-main">
						<div data-r="inboxhead" class="oa-inboxhead">
							<div>
								<div class="oa-inboxhead-title">{{ folderTitle }}</div>
								<div class="oa-inboxhead-sub">{{ faNum(filteredItems.length) }} نامه</div>
							</div>
							<div class="oa-spacer"></div>
							<div data-r="inboxsearch" class="oa-inboxsearch">
								<span class="ico">search</span>
								<input v-model="search" class="oa-searchinput" placeholder="جستجو در کارتابل…" aria-label="جستجو در کارتابل" />
							</div>
							<button @click="openCompose()" class="oa-primary-btn-sm h-primary"><span class="ico">add</span>نامه جدید</button>
						</div>
						<div class="oa-inbox-list">
							<div v-if="loading" class="oa-pad-empty">در حال بارگذاری…</div>
							<div v-else-if="!filteredItems.length" class="oa-pad-empty">موردی یافت نشد.</div>
							<button v-for="L in filteredItems" :key="L.name" @click="openItem(L)" class="oa-mailrow h-bord">
								<div class="oa-avatar oa-avatar-44" :style="{background:avatarColor(L.sender||L.recipient)}">{{ initials(L.sender||L.recipient) }}</div>
								<div class="oa-mailrow-body">
									<div class="oa-mailrow-titlerow">
										<span class="oa-mailrow-subject" :class="{ unseen: L.status==='Unseen' }">{{ L.reference_title || L.subject }}</span>
										<span v-if="L.referral_type" class="oa-chip-ref-inline" :style="refChip(L.referral_type)">{{ faType(L.referral_type) }}</span>
										<span v-if="L.urgency && L.urgency!=='Normal'" class="oa-chip oa-chip-urg"><span class="ico">bolt</span>{{ faUrg(L.urgency) }}</span>
									</div>
									<div class="oa-mailrow-sender">{{ scope==='outbox' ? ('به ' + L.recipient) : L.sender }}</div>
									<div v-if="L.instruction" class="oa-mailrow-instruction">{{ L.instruction }}</div>
								</div>
								<div class="oa-mailrow-meta">
									<span class="oa-mailrow-time">{{ shortDate(L.creation) }}</span>
									<span class="oa-mailrow-id">{{ L.reference_name }}</span>
								</div>
								<span v-if="L.status==='Unseen'" class="oa-unseen-dot"></span>
							</button>
						</div>
					</div>
				</div>

				<!-- LETTERS LIST -->
				<div v-else-if="view==='letters'" class="oa-letters">
					<div class="oa-breadcrumb">
						<button @click="goDashboard()" class="oa-crumb-btn">خانه</button>
						<span class="ico">chevron_left</span>
						<span class="oa-crumb-current">نامه‌های اتوماسیون</span>
					</div>
					<div data-r="dtable" class="oa-dtable">
						<div class="oa-dt-head">
							<span></span><span>موضوع</span><span>وضعیت</span><span>شماره</span><span>تاریخ</span><span>شناسه</span><span></span>
						</div>
						<div v-if="!letters.length" class="oa-pad-empty">نامه‌ای یافت نشد.</div>
						<button v-for="L in letters" :key="L.name" @click="openLetter(L.name)" class="oa-dtrow h-surface1">
							<span></span>
							<div class="oa-dt-subject">
								<div class="oa-avatar oa-avatar-34sq" :style="{background:avatarColor(L.sender)}">{{ initials(L.sender) }}</div>
								<div class="oa-minw0"><div class="oa-dt-subject-title">{{ L.subject }}</div><div class="oa-dt-subject-sender">{{ L.sender }}</div></div>
							</div>
							<span><span class="oa-chip oa-chip-status" :style="statusChip(L.status)">{{ faStatus(L.status) }}</span></span>
							<span class="oa-dt-muted">{{ L.letter_no || '—' }}</span>
							<span class="oa-dt-muted-ltr">{{ shortDate(L.date) }}</span>
							<span class="oa-dt-muted-id">{{ L.name }}</span>
							<span class="oa-dt-chev"><span class="ico">chevron_left</span></span>
						</button>
					</div>
				</div>

				<!-- LETTER VIEW -->
				<div v-else-if="view==='letter' && cur" class="oa-letter">
					<div class="oa-letter-top">
						<button @click="goInbox()" class="oa-backbtn h-surface1"><span class="ico">arrow_forward</span>بازگشت به کارتابل</button>
						<div class="oa-spacer"></div>
						<span class="oa-letter-id">{{ cur.name }}</span>
					</div>
					<div data-r="docgrid" class="oa-docgrid">
						<div class="oa-doccard">
							<div class="oa-dochead">
								<div class="oa-badges">
									<span class="oa-chip oa-chip-status-lg" :style="statusChip(cur.status)">{{ faStatus(cur.status) }}</span>
									<span v-if="cur.urgency && cur.urgency!=='Normal'" class="oa-chip oa-chip-urg-lg"><span class="ico">bolt</span>{{ faUrg(cur.urgency) }}</span>
									<span v-if="cur.confidentiality" class="oa-chip oa-chip-conf"><span class="ico">lock</span>{{ faConf(cur.confidentiality) }}</span>
								</div>
								<h1 class="oa-doc-subject">{{ cur.subject }}</h1>
								<div class="oa-doc-sender">
									<div class="oa-avatar oa-avatar-46" :style="{background:avatarColor(cur.sender)}">{{ initials(cur.sender) }}</div>
									<div class="oa-doc-sender-main"><div class="oa-doc-sender-name">{{ cur.sender_name }}</div><div class="oa-doc-sender-email">{{ cur.sender }}</div></div>
									<div class="oa-doc-date"><div class="oa-doc-date-val">{{ shortDate(cur.date) }}</div><div class="oa-doc-date-no">شماره نامه: {{ cur.letter_no || '—' }}</div></div>
								</div>
							</div>
							<div class="oa-doc-body">
								<p class="oa-doc-bism">بسمه تعالی</p>
								<div v-html="cur.body || ''"></div>
								<p class="oa-doc-sign">با احترام</p>
								<p class="oa-doc-signer">{{ cur.sender_name }}</p>
							</div>
							<div v-if="cur.attachments && cur.attachments.length" class="oa-attachments">
								<div class="oa-attachments-title"><span class="ico">attach_file</span>پیوست‌ها ({{ faNum(cur.attachments.length) }})</div>
								<div class="oa-attach-list">
									<a v-for="a in cur.attachments" :key="a.attachment" :href="a.attachment" target="_blank" class="oa-attach h-bord">
										<span class="ico oa-attach-ico">description</span>
										<div><div class="oa-attach-name">{{ a.title || a.attachment }}</div></div>
										<span class="ico oa-attach-dl">download</span>
									</a>
								</div>
							</div>
							<div data-r="actionbar" class="oa-actionbar">
								<button v-if="cur.status==='Draft' && cur.is_sender" @click="editCur()" class="oa-act-btn oa-act-primary h-primary"><span class="ico">edit</span>ویرایش</button>
								<button v-if="cur.status!=='Draft'" @click="referCur()" class="oa-act-btn oa-act-primary h-primary"><span class="ico">forward_to_inbox</span>ارجاع</button>
								<button v-if="cur.status!=='Draft'" @click="decideCur('approve')" class="oa-act-btn oa-act-approve"><span class="ico">check_circle</span>تأیید</button>
								<button v-if="cur.status!=='Draft'" @click="decideCur('reject')" class="oa-act-btn oa-act-reject"><span class="ico">cancel</span>رد</button>
								<button v-if="cur.status!=='Draft'" @click="decideCur('return')" class="oa-act-btn oa-act-return"><span class="ico">reply</span>عودت</button>
								<button v-if="cur.can_recall" @click="recallCur()" class="oa-act-btn oa-act-recall"><span class="ico">undo</span>بازپس‌گیری</button>
								<div class="oa-spacer"></div>
								<button @click="printLetter(cur.name)" class="oa-printbtn h-surface2" aria-label="چاپ"><span class="ico">print</span></button>
							</div>
						</div>
						<div class="oa-timeline">
							<div class="oa-timeline-head"><span class="ico">account_tree</span>گردش ارجاعات</div>
							<div class="oa-timeline-body">
								<div v-if="!cur.referrals.length" class="oa-timeline-empty">ارجاعی ثبت نشده.</div>
								<div v-for="(r,i) in cur.referrals" :key="r.name" class="oa-tl-node">
									<div class="oa-tl-dotcol">
										<div class="oa-tl-dot" :style="dotStyle(r)"><span class="ico">{{ dotIcon(r) }}</span></div>
										<div v-if="i < cur.referrals.length-1" class="oa-tl-line"></div>
									</div>
									<div class="oa-tl-content">
										<div class="oa-tl-sender">{{ r.sender_name }}</div>
										<div class="oa-tl-arrow"><span class="ico">south</span><span class="oa-chip oa-chip-ref-tl" :style="refChip(r.referral_type)">{{ faType(r.referral_type) }}</span></div>
										<div class="oa-tl-recipient">{{ r.recipient_name }}</div>
										<div v-if="r.instruction" class="oa-tl-instruction">«{{ r.instruction }}»</div>
										<div class="oa-tl-meta">
											<span class="oa-tl-time">{{ shortDate(r.creation) }}</span>
											<button v-if="r.can_recall" @click="recallRef(r)" title="بازپس‌گیری این ارجاع" class="oa-tl-recall"><span class="ico">undo</span>بازپس‌گیری</button>
										</div>
									</div>
								</div>
								<button v-if="cur.status!=='Draft'" @click="referCur()" class="oa-tl-add h-surface1"><span class="ico">add</span>ارجاع جدید</button>
							</div>
						</div>
					</div>
				</div>
			</main>
		</div>

		<!-- COMPOSE MODAL -->
		<NewLetterForm v-if="composeOpen" :refer-letter="composeLetter" :edit-letter="editName" @close="closeCompose" @created="onCreated" />

		<!-- REFERRAL (ERJA) MODAL -->
		<OaReferForm v-if="referOpen" :doctype="referCtx.doctype" :doc-name="referCtx.name" :parent="referCtx.parent" @close="closeRefer" @done="onReferred" />
	</div>
</template>

<script>
import NewLetterForm from "./NewLetterForm.vue";
import OaReferForm from "./OaReferForm.vue";

const API = "office_automation.office_automation.api.inbox.";
const LAPI = "office_automation.office_automation.api.letter.";
const REF = "office_automation.office_automation.doctype.document_referral.document_referral.";
const PALETTE = ["#1A56DB", "#7C3AED", "#0E9488", "#DB2777", "#D97706", "#2563EB", "#059669", "#DC2626"];
const FA_DIGITS = "۰۱۲۳۴۵۶۷۸۹";

export default {
	name: "OaPanel",
	components: { NewLetterForm, OaReferForm },
	data() {
		return {
			theme: "light",
			view: "dashboard",
			drawerOpen: false,
			folder: "inbox:all",
			scope: "inbox",
			statLabel: "",
			search: "",
			loading: false,
			stats: { unseen: 0, pending: 0, overdue: 0, today: 0 },
			counts: { inbox: {}, outbox: {}, drafts: 0 },
			pending: [],
			items: [],
			letters: [],
			cur: null,
			composeOpen: false,
			composeLetter: null,
			editName: null,
			referOpen: false,
			referCtx: null,
			meName: (frappe.user && frappe.user.full_name && frappe.user.full_name()) || frappe.session.user,
			meEmail: frappe.session.user,
			meRole: "اتوماسیون اداری",
		};
	},
	watch: {
		// On mobile, close the off-canvas drawer after navigating.
		view() {
			this.drawerOpen = false;
		},
	},
	computed: {
		meInitials() {
			return this.initials(this.meName);
		},
		todayStr() {
			try {
				return new Intl.DateTimeFormat("fa-IR", { weekday: "long", day: "numeric", month: "long", year: "numeric" }).format(new Date());
			} catch (e) {
				return "";
			}
		},
		menu() {
			return [
				{ key: "dashboard", label: "داشبورد", icon: "space_dashboard", go: () => this.goDashboard() },
				{ key: "inbox", label: "کارتابل", icon: "inbox", badge: this.stats.unseen, go: () => this.goInbox() },
				{ key: "letters", label: "نامه‌های اتوماسیون", icon: "description", go: () => this.goLetters() },
			];
		},
		masters() {
			return [
				{ label: "انواع نامه", icon: "label", go: () => this.route("Letter Type") },
				{ label: "انواع اقدام", icon: "bolt", go: () => this.route("Action Type") },
				{ label: "تنظیمات اتوماسیون", icon: "settings", go: () => this.routeForm("Office Automation Settings") },
			];
		},
		statCards() {
			// Each card carries the stat `kind`; clicking it opens the matching
			// referral list *inside* the Cartable (see openStat) — rendered by the
			// same inbox list as folders, not a route out to a desk list view.
			return [
				{ kind: "unseen", label: "ارجاعات دیده‌نشده", value: this.stats.unseen, color: "#D97706", tintBg: "rgba(232,147,12,.14)", icon: "visibility_off", note: "نیازمند مشاهده" },
				{ kind: "pending", label: "در انتظار اقدام", value: this.stats.pending, color: "#2563EB", tintBg: "rgba(37,99,235,.13)", icon: "hourglass_top", note: "در حال پیگیری" },
				{ kind: "overdue", label: "ارجاعات معوق", value: this.stats.overdue, color: "#DC2626", tintBg: "rgba(220,38,38,.13)", icon: "running_with_errors", note: "نیازمند رسیدگی فوری" },
				{ kind: "today", label: "نامه‌های امروز", value: this.stats.today, color: "#16A34A", tintBg: "rgba(22,163,74,.13)", icon: "mark_email_unread", note: "دریافت‌شده امروز" },
			];
		},
		shortcuts() {
			return [
				{ label: "کارتابل", icon: "inbox", count: null, go: () => this.goInbox() },
				{ label: "نامه اتوماسیون", icon: "description", count: this.counts.outbox?.all || 0, go: () => this.goLetters() },
				{ label: "ارجاع سند", icon: "forward_to_inbox", count: this.counts.inbox?.all || 0, go: () => this.goInbox() },
				{ label: "قانون تفویض", icon: "rule", count: null, go: () => this.route("Delegation Rule") },
			];
		},
		moduleGroups() {
			return [
				{ title: "مکاتبات", icon: "contract_edit", items: [
					{ label: "نامه اتوماسیون", icon: "description", go: () => this.goLetters() },
					{ label: "ارجاع سند", icon: "forward_to_inbox", go: () => this.route("Document Referral") },
				] },
				{ title: "کنترل دسترسی", icon: "admin_panel_settings", items: [
					{ label: "قانون تفویض", icon: "rule", go: () => this.route("Delegation Rule") },
					{ label: "تنظیمات اتوماسیون", icon: "settings", go: () => this.routeForm("Office Automation Settings") },
				] },
			];
		},
		folderGroups() {
			const c = this.counts;
			return [
				{ title: "کارتابل دریافتی (INBOX)", items: [
					{ key: "inbox:all", label: "همه", icon: "all_inbox", scope: "inbox", folder: "all", count: c.inbox?.all },
					{ key: "inbox:order", label: "دستور", icon: "gavel", scope: "inbox", folder: "order", count: c.inbox?.order },
					{ key: "inbox:followup", label: "پیگیری", icon: "follow_the_signs", scope: "inbox", folder: "followup", count: c.inbox?.followup },
					{ key: "inbox:action", label: "اقدام", icon: "task_alt", scope: "inbox", folder: "action", count: c.inbox?.action },
					{ key: "inbox:notification", label: "استحضار", icon: "visibility", scope: "inbox", folder: "notification", count: c.inbox?.notification },
					{ key: "inbox:info", label: "اطلاع", icon: "info", scope: "inbox", folder: "info", count: c.inbox?.info },
				] },
				{ title: "کارتابل ارسالی (OUTBOX)", items: [
					{ key: "outbox:all", label: "همه", icon: "send", scope: "outbox", state: "all", count: c.outbox?.all },
					{ key: "outbox:in_progress", label: "در دست اقدام", icon: "pending", scope: "outbox", state: "in_progress", count: c.outbox?.in_progress },
					{ key: "outbox:approved", label: "تأیید شده‌ها", icon: "check_circle", scope: "outbox", state: "approved", count: c.outbox?.approved },
					{ key: "outbox:rejected", label: "رد شده‌ها", icon: "cancel", scope: "outbox", state: "rejected", count: c.outbox?.rejected },
					{ key: "outbox:returned", label: "عودت‌شده‌ها", icon: "reply", scope: "outbox", state: "returned", count: c.outbox?.returned },
				] },
				{ title: "سایر", items: [
					{ key: "drafts", label: "پیش‌نویس‌ها", icon: "draft", scope: "drafts", count: c.drafts },
					{ key: "private", label: "خصوصی", icon: "lock", scope: "visibility", visibility: "private" },
					{ key: "public", label: "عمومی", icon: "public", scope: "visibility", visibility: "public" },
				] },
			];
		},
		folderTitle() {
			if (this.scope === "stat") return this.statLabel;
			for (const g of this.folderGroups) for (const f of g.items) if (f.key === this.folder) return f.label;
			return "کارتابل";
		},
		filteredItems() {
			const q = this.search.trim().toLowerCase();
			if (!q) return this.items;
			return this.items.filter((i) => [i.reference_title, i.subject, i.instruction, i.sender, i.recipient].filter(Boolean).join(" ").toLowerCase().includes(q));
		},
	},
	mounted() {
		this.loadDashboard();
		this._rt = () => { this.loadCounts(); if (this.view === "inbox") this.loadFolder(); };
		frappe.realtime.on("oa_inbox_update", this._rt);
	},
	beforeUnmount() {
		if (this._rt) frappe.realtime.off("oa_inbox_update", this._rt);
	},
	methods: {
		faNum(n) {
			return String(n ?? 0).replace(/\d/g, (d) => FA_DIGITS[+d]);
		},
		initials(x) {
			const s = (x || "").replace(/@.*/, "").trim();
			const parts = s.split(/[\s.]+/).filter(Boolean);
			return ((parts[0]?.[0] || "") + (parts[1]?.[0] || "")).toUpperCase() || "؟";
		},
		avatarColor(x) {
			let h = 0;
			for (const ch of x || "") h = (h * 31 + ch.charCodeAt(0)) >>> 0;
			return PALETTE[h % PALETTE.length];
		},
		shortDate(dt) {
			if (!dt) return "";
			try {
				return new Intl.DateTimeFormat("fa-IR", { day: "numeric", month: "short" }).format(new Date(dt));
			} catch (e) {
				return String(dt).slice(0, 10);
			}
		},
		faType(t) {
			return { Order: "دستور", "Follow-up": "پیگیری", Action: "اقدام", Notification: "استحضار", Info: "اطلاع" }[t] || t || "";
		},
		faStatus(s) {
			return { Unseen: "دیده‌نشده", Seen: "دیده‌شده", Actioned: "اتمام‌یافته", Draft: "پیش‌نویس", Registered: "ثبت‌شده", "In Progress": "در دست اقدام", Closed: "بسته‌شده", Cancelled: "باطل‌شده", Submitted: "ثبت‌شده" }[s] || s || "";
		},
		faUrg(u) {
			return { Urgent: "فوری", Immediate: "آنی", Normal: "عادی" }[u] || u;
		},
		faConf(c) {
			return { Confidential: "محرمانه", Secret: "سری", Normal: "عادی" }[c] || c;
		},
		refChip(t) {
			const m = {
				Order: ["rgba(124,58,237,.13)", "#7C3AED"], "Follow-up": ["rgba(217,119,6,.14)", "#D97706"],
				Action: ["rgba(37,99,235,.13)", "#2563EB"], Notification: ["rgba(14,148,136,.14)", "#0E9488"],
				Info: ["rgba(100,116,139,.16)", "#64748B"],
			};
			const [bg, fg] = m[t] || m.Info;
			return { background: bg, color: fg };
		},
		statusChip(s) {
			const open = ["Unseen", "Registered", "In Progress", "Submitted", "Seen"];
			if (s === "Closed" || s === "Actioned") return { background: "rgba(22,163,74,.13)", color: "#16A34A" };
			if (s === "Cancelled") return { background: "rgba(220,38,38,.13)", color: "#DC2626" };
			if (open.includes(s)) return { background: "rgba(37,99,235,.13)", color: "#2563EB" };
			return { background: "var(--surface-2)", color: "var(--on-variant)" };
		},
		dotStyle(r) {
			if (r.outcome === "Rejected") return { background: "rgba(220,38,38,.13)", color: "#DC2626" };
			if (r.outcome === "Returned") return { background: "rgba(2,132,199,.13)", color: "#0284C7" };
			if (r.outcome === "Approved" || r.status === "Actioned") return { background: "rgba(22,163,74,.15)", color: "#16A34A" };
			return { background: "var(--primary-container)", color: "var(--on-primary-container)" };
		},
		dotIcon(r) {
			if (r.outcome === "Rejected") return "close";
			if (r.outcome === "Returned") return "reply";
			if (r.outcome === "Approved" || r.status === "Actioned") return "check";
			return "forward_to_inbox";
		},
		route(doctype) {
			frappe.set_route("List", doctype);
		},
		openStat(card) {
			// Open a dashboard stat's referral list *inside* the Cartable (reusing
			// the inbox list rendering) rather than routing out to a desk list view.
			this.view = "inbox";
			this.scope = "stat";
			this.statLabel = card.label;
			this.folder = "stat:" + card.kind;
			this._active = { scope: "stat", kind: card.kind, key: this.folder };
			this.loadFolder();
		},
		routeForm(doctype) {
			frappe.set_route("Form", doctype);
		},
		printLetter(name) {
			window.open(`/printview?doctype=Automation Letter&name=${encodeURIComponent(name)}&format=Automation Letter Thread&no_letterhead=0`, "_blank");
		},
		async loadCounts() {
			try {
				this.counts = await frappe.xcall(API + "get_folder_counts");
				this.stats = await frappe.xcall(API + "get_dashboard_stats");
			} catch (e) { /* ignore */ }
		},
		async loadDashboard() {
			await this.loadCounts();
			try {
				this.pending = await frappe.xcall(API + "get_inbox_items", { folder: "all", limit: 5 });
			} catch (e) { this.pending = []; }
		},
		goDashboard() { this.view = "dashboard"; this.loadDashboard(); },
		goInbox() {
			// Always land on the full inbox, not a leftover stat/sub-folder view.
			this.view = "inbox";
			this.scope = "inbox";
			this.folder = "inbox:all";
			this._active = { scope: "inbox", folder: "all", key: "inbox:all" };
			this.loadCounts();
			this.loadFolder();
		},
		async goLetters() {
			this.view = "letters";
			try {
				this.letters = await frappe.db.get_list("Automation Letter", {
					fields: ["name", "subject", "sender", "status", "letter_no", "date"],
					order_by: "modified desc", limit: 50,
				});
			} catch (e) { this.letters = []; }
		},
		selectFolder(f) {
			this.folder = f.key;
			this.scope = f.scope;
			this._active = f;
			this.loadFolder();
		},
		async loadFolder() {
			const f = this._active || { scope: "inbox", folder: "all", key: "inbox:all" };
			this.scope = f.scope;
			this.loading = true;
			try {
				if (f.scope === "inbox") this.items = await frappe.xcall(API + "get_inbox_items", { folder: f.folder || "all" });
				else if (f.scope === "stat") this.items = await frappe.xcall(API + "get_referrals_by_stat", { kind: f.kind });
				else if (f.scope === "outbox") this.items = await frappe.xcall(API + "get_outbox_items", { state: f.state });
				else if (f.scope === "drafts") this.items = (await frappe.xcall(API + "get_drafts")).map((d) => ({ ...d, reference_name: d.name, reference_title: d.subject, status: "Draft" }));
				else if (f.scope === "visibility") this.items = (await frappe.xcall(API + "get_letters_by_visibility", { visibility: f.visibility })).map((d) => ({ ...d, reference_name: d.name, reference_title: d.subject }));
			} catch (e) { this.items = []; }
			finally { this.loading = false; }
		},
		async openItem(L) {
			// Drafts are editable: open the composer in edit mode instead of the
			// read-only letter view.
			if (this.scope === "drafts") { this.openEdit(L.reference_name || L.name); return; }
			if ((this.scope === "inbox" || this.scope === "stat") && L.status === "Unseen") {
				try { await frappe.xcall(REF + "mark_referral_seen", { referral: L.name }); } catch (e) { /* */ }
			}
			this.openLetter(L.reference_name || L.name);
		},
		async openLetter(name) {
			try {
				this.cur = await frappe.xcall(LAPI + "get_letter_detail", { name });
				this.view = "letter";
				this.loadCounts();
			} catch (e) {
				frappe.msgprint("امکان باز کردن نامه نبود.");
			}
		},
		openCompose(letter) {
			this.editName = null;
			this.composeLetter = letter || null;
			this.composeOpen = true;
		},
		openEdit(name) {
			this.composeLetter = null;
			this.editName = name;
			this.composeOpen = true;
		},
		editCur() {
			if (this.cur) this.openEdit(this.cur.name);
		},
		closeCompose() {
			this.composeOpen = false;
			this.editName = null;
			this.composeLetter = null;
		},
		onCreated(res) {
			this.composeOpen = false;
			this.editName = null;
			this.composeLetter = null;
			if (res && res.refer && res.name) {
				this.forwardDialog("Automation Letter", res.name, null);
			}
			this.loadCounts();
			if (this.view === "letter" && res && res.name) this.openLetter(res.name);
			else if (this.view === "inbox") this.loadFolder();
			else if (this.view === "dashboard") this.loadDashboard();
		},
		async decideCur(kind) {
			// Act on the current user's open referral for this letter.
			const mine = (this.cur.referrals || []).find((r) => r.recipient === this.meEmail && ["Unseen", "Seen"].includes(r.status));
			if (!mine) { frappe.msgprint("ارجاع بازی برای شما روی این نامه وجود ندارد."); return; }
			const CFG = {
				approve: { method: "approve_referral", title: "تأیید ارجاع", label: "تأیید", done: "تأیید شد", indicator: "green" },
				reject: { method: "reject_referral", title: "رد ارجاع", label: "رد", done: "رد شد", indicator: "red" },
				return: { method: "return_referral", title: "عودت ارجاع", label: "عودت", done: "عودت شد", indicator: "blue" },
			}[kind];
			const d = new frappe.ui.Dialog({
				title: CFG.title,
				fields: [{ label: "یادداشت", fieldname: "note", fieldtype: "Small Text" }],
				primary_action_label: CFG.label,
				primary_action: async (v) => {
					await frappe.xcall(REF + CFG.method, { referral: mine.name, note: v.note });
					d.hide();
					frappe.show_alert({ message: CFG.done, indicator: CFG.indicator });
					this.openLetter(this.cur.name);
				},
			});
			d.show();
		},
		referCur() {
			const mine = (this.cur.referrals || []).find((r) => r.recipient === this.meEmail && ["Unseen", "Seen"].includes(r.status));
			this.forwardDialog("Automation Letter", this.cur.name, mine ? mine.name : null);
		},
		runRecall(confirmMsg, apiMethod, params, successMsg) {
			// Shared confirm → recall → refresh → error scaffold for both the
			// whole-letter and per-recipient recall actions.
			frappe.confirm(confirmMsg, async () => {
				try {
					const res = await frappe.xcall(REF + apiMethod, params);
					frappe.show_alert({ message: successMsg(res), indicator: "orange" });
					this.loadCounts();
					this.openLetter(this.cur.name);
				} catch (e) {
					frappe.msgprint((e && e.message) || "امکان بازپس‌گیری نبود.");
				}
			});
		},
		recallCur() {
			// Sender unsends the letter: pull it back from every recipient who has
			// not opened it yet. If nobody opened it, the letter returns to Draft.
			const n = this.cur.unseen_count || 0;
			const msg = `این نامه از کارتابل ${this.faNum(n)} گیرنده‌ای که هنوز آن را باز نکرده‌اند بازپس گرفته می‌شود. ادامه می‌دهید؟`;
			this.runRecall(msg, "recall_letter", { reference_name: this.cur.name }, (res) =>
				res.reverted_to_draft
					? "نامه بازپس گرفته شد و به پیش‌نویس بازگشت."
					: `از ${this.faNum(res.recalled)} گیرنده بازپس گرفته شد؛ ${this.faNum(res.kept)} گیرنده قبلاً آن را باز کرده‌اند.`,
			);
		},
		recallRef(r) {
			this.runRecall(
				`این ارجاع از کارتابل ${r.recipient_name} بازپس گرفته شود؟`,
				"recall_referral",
				{ referral: r.name },
				() => "بازپس گرفته شد",
			);
		},
		forwardDialog(doctype, name, parent) {
			// Open the themed custom Erja modal (OaReferForm) instead of the stock
			// frappe.ui.Dialog, so it matches the panel's look & feel.
			this.referCtx = { doctype, name, parent };
			this.referOpen = true;
		},
		closeRefer() {
			this.referOpen = false;
			this.referCtx = null;
		},
		onReferred() {
			const name = this.referCtx && this.referCtx.name;
			this.closeRefer();
			if (this.view === "letter" && name) this.openLetter(name);
			else this.loadFolder();
			this.loadCounts();
		},
	},
};
</script>
