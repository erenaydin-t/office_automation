<template>
	<div class="oa-panel" :data-theme="theme" dir="rtl" lang="fa">

		<!-- ============ TOP APP BAR ============ -->
		<header data-r="appbar" style="height:64px;flex:none;display:flex;align-items:center;gap:16px;padding:0 20px;background:var(--surface);border-bottom:1px solid var(--outline-soft);box-shadow:var(--elev1);z-index:20">
			<button data-r="burger" @click="drawerOpen=!drawerOpen" class="h-surface1" style="display:none;align-items:center;justify-content:center;width:40px;height:40px;border:none;border-radius:11px;background:var(--surface-1);color:var(--on-variant);cursor:pointer"><span class="ico" style="font-size:22px">menu</span></button>
			<div data-r="logowrap" style="display:flex;align-items:center;gap:12px;min-width:200px">
				<div style="width:40px;height:40px;border-radius:11px;background:linear-gradient(135deg,var(--primary),var(--primary-strong));display:flex;align-items:center;justify-content:center;box-shadow:var(--elev1)">
					<span class="ico" style="font-size:22px;color:#fff">mail</span>
				</div>
				<div style="display:flex;flex-direction:column;line-height:1.2">
					<span style="font-size:15px;font-weight:700">اتوماسیون اداری</span>
					<span style="font-size:11.5px;color:var(--on-faint);font-weight:500">Office Automation</span>
				</div>
			</div>
			<div data-r="topsearch" style="flex:1;max-width:520px;display:flex;align-items:center;gap:8px;height:42px;padding:0 14px;background:var(--surface-1);border:1px solid var(--outline-soft);border-radius:12px">
				<span class="ico" style="font-size:20px;color:var(--on-faint)">search</span>
				<input v-model="search" placeholder="جستجوی نامه، شماره، فرستنده…" style="flex:1;border:none;outline:none;background:transparent;color:var(--on-surface);font-size:13.5px;font-family:inherit"/>
			</div>
			<div style="flex:1"></div>
			<div style="display:flex;align-items:center;gap:6px">
				<button @click="toggleTheme" title="حالت روشن/تیره" class="h-surface2" style="width:42px;height:42px;border:none;border-radius:11px;background:var(--surface-1);color:var(--on-variant);cursor:pointer;display:flex;align-items:center;justify-content:center">
					<span class="ico" style="font-size:21px">{{ theme === 'dark' ? 'light_mode' : 'dark_mode' }}</span>
				</button>
				<div data-r="profchip" style="display:flex;align-items:center;gap:9px;padding:4px 10px 4px 4px;border-radius:30px;background:var(--surface-1);cursor:pointer">
					<div style="width:34px;height:34px;border-radius:50%;background:linear-gradient(135deg,#1A56DB,#5B8DEF);color:#fff;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:13px">{{ meInitials }}</div>
					<div data-r="profmeta" style="display:flex;flex-direction:column;line-height:1.25;padding-left:4px">
						<span style="font-size:12.5px;font-weight:600">{{ meName }}</span>
						<span style="font-size:10.5px;color:var(--on-faint)">{{ meRole }}</span>
					</div>
				</div>
			</div>
		</header>

		<div style="flex:1;display:flex;min-height:0">
			<!-- ============ NAV DRAWER ============ -->
			<nav data-r="drawer" :data-open="drawerOpen ? '1' : '0'" style="width:256px;flex:none;background:var(--surface);border-left:1px solid var(--outline-soft);display:flex;flex-direction:column;padding:16px 14px;gap:4px;overflow:auto">
				<button @click="openCompose()" class="h-primary" style="display:flex;align-items:center;justify-content:center;gap:8px;height:48px;margin-bottom:12px;border:none;border-radius:14px;background:var(--primary);color:var(--on-primary);font-family:inherit;font-size:14px;font-weight:700;cursor:pointer;box-shadow:var(--elev2)">
					<span class="ico" style="font-size:21px">edit_square</span>ایجاد نامه جدید
				</button>
				<span style="font-size:11px;font-weight:700;color:var(--on-faint);padding:8px 12px 4px">منو</span>
				<button v-for="m in menu" :key="m.key" @click="m.go()" class="h-surface1"
					:style="navStyle(m.key)"
					style="display:flex;align-items:center;gap:13px;height:46px;padding:0 14px;border:none;border-radius:13px;font-family:inherit;font-size:13.5px;font-weight:600;cursor:pointer;text-align:right">
					<span class="ico" style="font-size:22px">{{ m.icon }}</span>{{ m.label }}
					<span v-if="m.badge" style="margin-right:auto;font-size:11px;font-weight:700;background:#E8533A;color:#fff;border-radius:20px;padding:1px 8px">{{ faNum(m.badge) }}</span>
				</button>
				<span style="font-size:11px;font-weight:700;color:var(--on-faint);padding:14px 12px 4px">داده‌های پایه</span>
				<button v-for="m in masters" :key="m.label" @click="m.go()" class="h-surface1" style="display:flex;align-items:center;gap:13px;height:42px;padding:0 14px;border:none;border-radius:13px;font-family:inherit;font-size:13px;font-weight:600;cursor:pointer;text-align:right;background:transparent;color:var(--on-variant)">
					<span class="ico" style="font-size:21px">{{ m.icon }}</span>{{ m.label }}
				</button>
			</nav>
			<div data-r="navscrim" :data-open="drawerOpen ? '1' : '0'" @click="drawerOpen=false" style="display:none;position:fixed;inset:64px 0 0 0;background:var(--scrim);z-index:54"></div>

			<!-- ============ MAIN ============ -->
			<main style="flex:1;overflow:auto;min-width:0">
				<!-- DASHBOARD -->
				<div v-if="view==='dashboard'" style="max-width:1180px;margin:0 auto;padding:32px 36px 56px;animation:oaFade .3s ease">
					<div data-r="dashhead" style="display:flex;align-items:flex-end;justify-content:space-between;gap:16px;margin-bottom:26px">
						<div>
							<div style="font-size:13px;color:var(--on-faint);font-weight:600;margin-bottom:4px">{{ todayStr }}</div>
							<h1 style="margin:0;font-size:26px;font-weight:800;letter-spacing:-.3px">سلام {{ meName }}، خلاصهٔ کارتابل امروز</h1>
						</div>
						<button @click="openCompose()" class="h-primary" style="display:flex;align-items:center;gap:8px;height:46px;padding:0 20px;border:none;border-radius:13px;background:var(--primary);color:var(--on-primary);font-family:inherit;font-size:13.5px;font-weight:700;cursor:pointer;box-shadow:var(--elev2)">
							<span class="ico" style="font-size:20px">add</span>نامه جدید
						</button>
					</div>
					<div data-r="grid4" style="display:grid;grid-template-columns:repeat(4,1fr);gap:18px;margin-bottom:30px">
						<div v-for="c in statCards" :key="c.label" style="background:var(--surface);border:1px solid var(--outline-soft);border-radius:18px;padding:20px;box-shadow:var(--elev1)">
							<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:14px">
								<span style="font-size:13px;color:var(--on-variant);font-weight:600">{{ c.label }}</span>
								<div style="width:38px;height:38px;border-radius:11px;display:flex;align-items:center;justify-content:center" :style="{background:c.tintBg}"><span class="ico" style="font-size:21px" :style="{color:c.color}">{{ c.icon }}</span></div>
							</div>
							<div style="font-size:38px;font-weight:800;line-height:1" :style="{color:c.color}">{{ faNum(c.value) }}</div>
							<div style="margin-top:10px;font-size:11.5px;color:var(--on-faint)">{{ c.note }}</div>
						</div>
					</div>

					<div style="font-size:13px;font-weight:700;color:var(--on-variant);margin-bottom:12px">دسترسی سریع</div>
					<div data-r="grid4" style="display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:30px">
						<button v-for="s in shortcuts" :key="s.label" @click="s.go()" class="h-bord" style="display:flex;align-items:center;gap:12px;padding:16px 18px;background:var(--surface);border:1px solid var(--outline-soft);border-radius:15px;cursor:pointer;font-family:inherit;box-shadow:var(--elev1)">
							<div style="width:40px;height:40px;border-radius:11px;background:var(--primary-container);display:flex;align-items:center;justify-content:center"><span class="ico" style="font-size:22px;color:var(--on-primary-container)">{{ s.icon }}</span></div>
							<span style="font-size:13.5px;font-weight:700;color:var(--on-surface)">{{ s.label }}</span>
							<span v-if="s.count!=null" style="margin-right:auto;font-size:11px;font-weight:700;color:var(--on-variant);background:var(--surface-2);border-radius:20px;padding:2px 9px">{{ faNum(s.count) }}</span>
							<span v-else class="ico" style="margin-right:auto;font-size:18px;color:var(--on-faint)">north_east</span>
						</button>
					</div>

					<div data-r="grid2" style="display:grid;grid-template-columns:1.5fr 1fr;gap:20px">
						<div style="background:var(--surface);border:1px solid var(--outline-soft);border-radius:18px;box-shadow:var(--elev1);overflow:hidden">
							<div style="display:flex;align-items:center;justify-content:space-between;padding:18px 20px;border-bottom:1px solid var(--outline-soft)">
								<span style="font-size:14.5px;font-weight:700">در انتظار اقدام شما</span>
								<button @click="goInbox()" style="border:none;background:transparent;color:var(--primary);font-family:inherit;font-size:12.5px;font-weight:700;cursor:pointer">مشاهده همه</button>
							</div>
							<div v-if="!pending.length" style="padding:28px;text-align:center;color:var(--on-faint);font-size:13px">موردی نیست.</div>
							<div v-for="row in pending" :key="row.name" @click="openLetter(row.reference_name)" class="h-surface1" style="display:flex;align-items:center;gap:13px;padding:14px 20px;border-bottom:1px solid var(--outline-soft);cursor:pointer">
								<div style="width:40px;height:40px;border-radius:11px;flex:none;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:13px;color:#fff" :style="{background:avatarColor(row.sender)}">{{ initials(row.sender) }}</div>
								<div style="min-width:0;flex:1">
									<div style="font-size:13.5px;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{{ row.reference_title }}</div>
									<div style="font-size:11.5px;color:var(--on-faint);margin-top:2px">{{ row.sender }}</div>
								</div>
								<span style="font-size:11px;font-weight:700;padding:3px 11px;border-radius:20px" :style="refChip(row.referral_type)">{{ faType(row.referral_type) }}</span>
								<span style="font-size:11px;color:var(--on-faint);white-space:nowrap">{{ shortDate(row.creation) }}</span>
							</div>
						</div>
						<div style="display:flex;flex-direction:column;gap:20px">
							<div v-for="g in moduleGroups" :key="g.title" style="background:var(--surface);border:1px solid var(--outline-soft);border-radius:18px;box-shadow:var(--elev1);padding:18px 20px">
								<div style="font-size:13.5px;font-weight:700;margin-bottom:12px;display:flex;align-items:center;gap:8px"><span class="ico" style="font-size:19px;color:var(--primary)">{{ g.icon }}</span>{{ g.title }}</div>
								<button v-for="it in g.items" :key="it.label" @click="it.go()" class="h-surface1" style="display:flex;width:100%;align-items:center;gap:10px;padding:9px 8px;border:none;background:transparent;border-radius:9px;font-family:inherit;font-size:12.5px;font-weight:600;color:var(--on-variant);cursor:pointer;text-align:right"><span class="ico" style="font-size:18px;color:var(--on-faint)">{{ it.icon }}</span>{{ it.label }}<span class="ico" style="margin-right:auto;font-size:16px;color:var(--on-faint)">north_east</span></button>
							</div>
						</div>
					</div>
				</div>

				<!-- INBOX -->
				<div v-else-if="view==='inbox'" style="display:flex;height:100%;min-height:0;animation:oaFade .3s ease">
					<div data-r="folderpane" style="width:248px;flex:none;border-left:1px solid var(--outline-soft);background:var(--surface);overflow:auto;padding:16px 12px">
						<div v-for="grp in folderGroups" :key="grp.title" style="margin-bottom:8px">
							<div style="font-size:11px;font-weight:700;color:var(--on-faint);padding:10px 12px 6px">{{ grp.title }}</div>
							<button v-for="f in grp.items" :key="f.key" @click="selectFolder(f)" class="h-surface1"
								:style="folder===f.key ? 'background:var(--primary-container);color:var(--on-primary-container)' : 'background:transparent;color:var(--on-variant)'"
								style="display:flex;width:100%;align-items:center;gap:11px;height:40px;padding:0 12px;border:none;border-radius:11px;font-family:inherit;font-size:13px;font-weight:600;cursor:pointer;text-align:right">
								<span class="ico" style="font-size:19px">{{ f.icon }}</span>{{ f.label }}
								<span v-if="f.count" style="margin-right:auto;font-size:11px;font-weight:700">{{ faNum(f.count) }}</span>
							</button>
						</div>
					</div>
					<div style="flex:1;display:flex;flex-direction:column;min-width:0">
						<div data-r="inboxhead" style="display:flex;align-items:center;gap:14px;padding:18px 24px;border-bottom:1px solid var(--outline-soft);background:var(--surface)">
							<div>
								<div style="font-size:17px;font-weight:800">{{ folderTitle }}</div>
								<div style="font-size:12px;color:var(--on-faint);margin-top:2px">{{ faNum(filteredItems.length) }} نامه</div>
							</div>
							<div style="flex:1"></div>
							<div data-r="inboxsearch" style="display:flex;align-items:center;gap:8px;height:40px;padding:0 12px;background:var(--surface-1);border:1px solid var(--outline-soft);border-radius:11px;width:240px">
								<span class="ico" style="font-size:19px;color:var(--on-faint)">search</span>
								<input v-model="search" placeholder="جستجو در کارتابل…" style="flex:1;border:none;outline:none;background:transparent;color:var(--on-surface);font-size:13px;font-family:inherit"/>
							</div>
							<button @click="openCompose()" class="h-primary" style="display:flex;align-items:center;gap:7px;height:40px;padding:0 16px;border:none;border-radius:11px;background:var(--primary);color:var(--on-primary);font-family:inherit;font-size:13px;font-weight:700;cursor:pointer;box-shadow:var(--elev1)"><span class="ico" style="font-size:19px">add</span>نامه جدید</button>
						</div>
						<div style="flex:1;overflow:auto;padding:14px 20px">
							<div v-if="loading" style="padding:40px;text-align:center;color:var(--on-faint)">در حال بارگذاری…</div>
							<div v-else-if="!filteredItems.length" style="padding:40px;text-align:center;color:var(--on-faint)">موردی یافت نشد.</div>
							<div v-for="L in filteredItems" :key="L.name" @click="openItem(L)" class="h-bord" style="display:flex;align-items:flex-start;gap:14px;padding:16px 18px;margin-bottom:10px;background:var(--surface);border:1px solid var(--outline-soft);border-radius:15px;cursor:pointer;box-shadow:var(--elev1);position:relative">
								<div style="width:44px;height:44px;border-radius:12px;flex:none;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:14px;color:#fff" :style="{background:avatarColor(L.sender||L.recipient)}">{{ initials(L.sender||L.recipient) }}</div>
								<div style="flex:1;min-width:0">
									<div style="display:flex;align-items:center;gap:9px;margin-bottom:4px">
										<span :style="{fontWeight: L.status==='Unseen' ? 800 : 600}" style="font-size:14px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{{ L.reference_title || L.subject }}</span>
										<span v-if="L.referral_type" style="font-size:11px;font-weight:700;padding:2px 10px;border-radius:20px;flex:none" :style="refChip(L.referral_type)">{{ faType(L.referral_type) }}</span>
										<span v-if="L.urgency && L.urgency!=='Normal'" style="font-size:10.5px;font-weight:700;padding:2px 9px;border-radius:20px;flex:none;background:rgba(220,38,38,.13);color:#DC2626;display:flex;align-items:center;gap:3px"><span class="ico" style="font-size:13px">bolt</span>{{ faUrg(L.urgency) }}</span>
									</div>
									<div style="font-size:12.5px;color:var(--on-variant);margin-bottom:6px;font-weight:600">{{ scope==='outbox' ? ('به ' + L.recipient) : L.sender }}</div>
									<div v-if="L.instruction" style="font-size:12.5px;color:var(--on-faint);white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{{ L.instruction }}</div>
								</div>
								<div style="display:flex;flex-direction:column;align-items:flex-start;gap:8px;flex:none">
									<span style="font-size:11.5px;color:var(--on-faint);white-space:nowrap">{{ shortDate(L.creation) }}</span>
									<span style="font-size:11px;color:var(--on-faint);direction:ltr">{{ L.reference_name }}</span>
								</div>
								<span v-if="L.status==='Unseen'" style="position:absolute;top:18px;right:6px;width:8px;height:8px;border-radius:50%;background:var(--primary)"></span>
							</div>
						</div>
					</div>
				</div>

				<!-- LETTERS LIST -->
				<div v-else-if="view==='letters'" style="padding:24px 32px 48px;animation:oaFade .3s ease">
					<div style="display:flex;align-items:center;gap:10px;font-size:12.5px;color:var(--on-faint);margin-bottom:18px">
						<button @click="goDashboard()" style="border:none;background:transparent;color:var(--on-faint);cursor:pointer;font-family:inherit;font-size:12.5px;padding:0">خانه</button>
						<span class="ico" style="font-size:16px">chevron_left</span>
						<span style="color:var(--on-surface);font-weight:700">نامه‌های اتوماسیون</span>
					</div>
					<div data-r="dtable" style="background:var(--surface);border:1px solid var(--outline-soft);border-radius:18px;box-shadow:var(--elev1);overflow:hidden">
						<div style="display:grid;grid-template-columns:38px 2.4fr 1fr .9fr 1fr 1.1fr 48px;align-items:center;padding:0 20px;height:46px;background:var(--surface-1);font-size:12px;font-weight:700;color:var(--on-variant)">
							<span></span><span>موضوع</span><span>وضعیت</span><span>شماره</span><span>تاریخ</span><span>شناسه</span><span></span>
						</div>
						<div v-if="!letters.length" style="padding:40px;text-align:center;color:var(--on-faint)">نامه‌ای یافت نشد.</div>
						<div v-for="L in letters" :key="L.name" @click="openLetter(L.name)" class="h-surface1" style="display:grid;grid-template-columns:38px 2.4fr 1fr .9fr 1fr 1.1fr 48px;align-items:center;padding:0 20px;height:62px;border-top:1px solid var(--outline-soft);cursor:pointer;font-size:13px">
							<span></span>
							<div style="display:flex;align-items:center;gap:12px;min-width:0">
								<div style="width:34px;height:34px;border-radius:9px;flex:none;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:12px;color:#fff" :style="{background:avatarColor(L.sender)}">{{ initials(L.sender) }}</div>
								<div style="min-width:0"><div style="font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{{ L.subject }}</div><div style="font-size:11.5px;color:var(--on-faint)">{{ L.sender }}</div></div>
							</div>
							<span><span style="font-size:11.5px;font-weight:700;padding:3px 11px;border-radius:20px" :style="statusChip(L.status)">{{ faStatus(L.status) }}</span></span>
							<span style="color:var(--on-variant);font-weight:600">{{ L.letter_no || '—' }}</span>
							<span style="color:var(--on-variant);direction:ltr">{{ shortDate(L.date) }}</span>
							<span style="color:var(--on-variant);direction:ltr;font-weight:600">{{ L.name }}</span>
							<span style="display:flex;justify-content:center"><span class="ico" style="font-size:19px;color:var(--on-faint)">chevron_left</span></span>
						</div>
					</div>
				</div>

				<!-- LETTER VIEW -->
				<div v-else-if="view==='letter' && cur" style="max-width:1080px;margin:0 auto;padding:22px 32px 56px;animation:oaFade .3s ease">
					<div style="display:flex;align-items:center;gap:12px;margin-bottom:18px">
						<button @click="goInbox()" class="h-surface1" style="display:flex;align-items:center;gap:7px;height:38px;padding:0 14px;border:1px solid var(--outline-soft);border-radius:11px;background:var(--surface);color:var(--on-variant);font-family:inherit;font-size:12.5px;font-weight:700;cursor:pointer"><span class="ico" style="font-size:18px">arrow_forward</span>بازگشت به کارتابل</button>
						<div style="flex:1"></div>
						<span style="font-size:12px;color:var(--on-faint);direction:ltr">{{ cur.name }}</span>
					</div>
					<div data-r="docgrid" style="display:grid;grid-template-columns:1fr 320px;gap:22px;align-items:start">
						<div style="background:var(--surface);border:1px solid var(--outline-soft);border-radius:20px;box-shadow:var(--elev1);overflow:hidden">
							<div style="padding:26px 30px 22px;border-bottom:1px solid var(--outline-soft)">
								<div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:14px">
									<span style="font-size:11.5px;font-weight:700;padding:3px 12px;border-radius:20px" :style="statusChip(cur.status)">{{ faStatus(cur.status) }}</span>
									<span v-if="cur.urgency && cur.urgency!=='Normal'" style="font-size:11.5px;font-weight:700;padding:3px 12px;border-radius:20px;background:rgba(220,38,38,.13);color:#DC2626;display:flex;align-items:center;gap:4px"><span class="ico" style="font-size:14px">bolt</span>{{ faUrg(cur.urgency) }}</span>
									<span v-if="cur.confidentiality" style="font-size:11.5px;font-weight:700;padding:3px 12px;border-radius:20px;background:var(--surface-2);color:var(--on-variant);display:flex;align-items:center;gap:4px"><span class="ico" style="font-size:14px">lock</span>{{ faConf(cur.confidentiality) }}</span>
								</div>
								<h1 style="margin:0 0 16px;font-size:23px;font-weight:800;letter-spacing:-.3px">{{ cur.subject }}</h1>
								<div style="display:flex;align-items:center;gap:13px">
									<div style="width:46px;height:46px;border-radius:13px;flex:none;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:15px;color:#fff" :style="{background:avatarColor(cur.sender)}">{{ initials(cur.sender) }}</div>
									<div style="flex:1"><div style="font-size:14px;font-weight:700">{{ cur.sender_name }}</div><div style="font-size:12px;color:var(--on-faint)">{{ cur.sender }}</div></div>
									<div style="text-align:left"><div style="font-size:12.5px;color:var(--on-variant);font-weight:600;direction:ltr">{{ shortDate(cur.date) }}</div><div style="font-size:11.5px;color:var(--on-faint)">شماره نامه: {{ cur.letter_no || '—' }}</div></div>
								</div>
							</div>
							<div style="padding:28px 30px;font-size:14px;line-height:2.05;color:var(--on-surface)">
								<p style="margin:0 0 14px;font-weight:700">بسمه تعالی</p>
								<div v-html="cur.body || ''"></div>
								<p style="margin:24px 0 0;font-weight:700">با احترام</p>
								<p style="margin:4px 0 0;color:var(--on-variant)">{{ cur.sender_name }}</p>
							</div>
							<div v-if="cur.attachments && cur.attachments.length" style="padding:0 30px 26px">
								<div style="font-size:12.5px;font-weight:700;color:var(--on-variant);margin-bottom:10px;display:flex;align-items:center;gap:7px"><span class="ico" style="font-size:18px">attach_file</span>پیوست‌ها ({{ faNum(cur.attachments.length) }})</div>
								<div style="display:flex;gap:10px;flex-wrap:wrap">
									<a v-for="a in cur.attachments" :key="a.attachment" :href="a.attachment" target="_blank" class="h-bord" style="display:flex;align-items:center;gap:10px;padding:10px 14px;background:var(--surface-1);border:1px solid var(--outline-soft);border-radius:12px;cursor:pointer;text-decoration:none;color:inherit">
										<span class="ico" style="font-size:24px;color:var(--primary)">description</span>
										<div><div style="font-size:12.5px;font-weight:600">{{ a.title || a.attachment }}</div></div>
										<span class="ico" style="font-size:19px;color:var(--on-faint)">download</span>
									</a>
								</div>
							</div>
							<div data-r="actionbar" style="display:flex;gap:10px;padding:18px 30px;border-top:1px solid var(--outline-soft);background:var(--surface-1)">
								<button @click="referCur()" class="h-primary" style="display:flex;align-items:center;gap:7px;height:42px;padding:0 18px;border:none;border-radius:12px;background:var(--primary);color:var(--on-primary);font-family:inherit;font-size:13px;font-weight:700;cursor:pointer;box-shadow:var(--elev1)"><span class="ico" style="font-size:19px">forward_to_inbox</span>ارجاع</button>
								<button @click="decideCur('approve')" style="display:flex;align-items:center;gap:7px;height:42px;padding:0 18px;border:1px solid rgba(22,163,74,.4);border-radius:12px;background:rgba(22,163,74,.1);color:#16A34A;font-family:inherit;font-size:13px;font-weight:700;cursor:pointer"><span class="ico" style="font-size:19px">check_circle</span>تأیید</button>
								<button @click="decideCur('reject')" style="display:flex;align-items:center;gap:7px;height:42px;padding:0 18px;border:1px solid rgba(220,38,38,.4);border-radius:12px;background:rgba(220,38,38,.08);color:#DC2626;font-family:inherit;font-size:13px;font-weight:700;cursor:pointer"><span class="ico" style="font-size:19px">cancel</span>رد</button>
								<div style="flex:1"></div>
								<button @click="printLetter(cur.name)" class="h-surface2" style="width:42px;height:42px;border:1px solid var(--outline-soft);border-radius:12px;background:var(--surface);color:var(--on-variant);cursor:pointer"><span class="ico" style="font-size:19px">print</span></button>
							</div>
						</div>
						<div style="background:var(--surface);border:1px solid var(--outline-soft);border-radius:20px;box-shadow:var(--elev1);overflow:hidden;position:sticky;top:10px">
							<div style="padding:18px 20px;border-bottom:1px solid var(--outline-soft);font-size:14px;font-weight:700;display:flex;align-items:center;gap:8px"><span class="ico" style="font-size:20px;color:var(--primary)">account_tree</span>گردش ارجاعات</div>
							<div style="padding:20px">
								<div v-if="!cur.referrals.length" style="color:var(--on-faint);font-size:12.5px;text-align:center;padding:10px 0 18px">ارجاعی ثبت نشده.</div>
								<div v-for="(r,i) in cur.referrals" :key="r.name" style="display:flex;gap:13px;position:relative;padding-bottom:22px">
									<div style="display:flex;flex-direction:column;align-items:center;flex:none">
										<div style="width:34px;height:34px;border-radius:50%;display:flex;align-items:center;justify-content:center;z-index:1" :style="dotStyle(r)"><span class="ico" style="font-size:18px">{{ dotIcon(r) }}</span></div>
										<div v-if="i < cur.referrals.length-1" style="width:2px;flex:1;background:var(--outline-soft);margin-top:4px"></div>
									</div>
									<div style="flex:1;min-width:0;padding-top:2px">
										<div style="font-size:12.5px;font-weight:700">{{ r.sender_name }}</div>
										<div style="display:flex;align-items:center;gap:6px;margin:6px 0"><span class="ico" style="font-size:14px;color:var(--on-faint)">south</span><span style="font-size:11.5px;font-weight:700;padding:1px 9px;border-radius:20px" :style="refChip(r.referral_type)">{{ faType(r.referral_type) }}</span></div>
										<div style="font-size:12.5px;font-weight:700;color:var(--on-surface)">{{ r.recipient_name }}</div>
										<div v-if="r.instruction" style="margin-top:8px;font-size:12px;color:var(--on-variant);background:var(--surface-1);border-radius:10px;padding:8px 11px;line-height:1.7">«{{ r.instruction }}»</div>
										<div style="font-size:10.5px;color:var(--on-faint);margin-top:6px;direction:ltr;text-align:right">{{ shortDate(r.creation) }}</div>
									</div>
								</div>
								<button @click="referCur()" class="h-surface1" style="display:flex;width:100%;align-items:center;justify-content:center;gap:7px;height:40px;border:1px dashed var(--outline);border-radius:12px;background:transparent;color:var(--primary);font-family:inherit;font-size:12.5px;font-weight:700;cursor:pointer"><span class="ico" style="font-size:18px">add</span>ارجاع جدید</button>
							</div>
						</div>
					</div>
				</div>
			</main>
		</div>

		<!-- COMPOSE MODAL -->
		<NewLetterForm v-if="composeOpen" :refer-letter="composeLetter" @close="composeOpen=false" @created="onCreated" />
	</div>
</template>

<script>
import NewLetterForm from "./NewLetterForm.vue";

const API = "office_automation.office_automation.api.inbox.";
const LAPI = "office_automation.office_automation.api.letter.";
const REF = "office_automation.office_automation.doctype.document_referral.document_referral.";
const PALETTE = ["#1A56DB", "#7C3AED", "#0E9488", "#DB2777", "#D97706", "#2563EB", "#059669", "#DC2626"];
const FA_DIGITS = "۰۱۲۳۴۵۶۷۸۹";

export default {
	name: "OaPanel",
	components: { NewLetterForm },
	data() {
		return {
			theme: localStorage.getItem("oa_theme") || "light",
			view: "dashboard",
			drawerOpen: false,
			folder: "inbox:all",
			scope: "inbox",
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
			return [
				{ label: "ارجاعات دیده‌نشده", value: this.stats.unseen, color: "#D97706", tintBg: "rgba(232,147,12,.14)", icon: "visibility_off", note: "نیازمند مشاهده" },
				{ label: "در انتظار اقدام", value: this.stats.pending, color: "#2563EB", tintBg: "rgba(37,99,235,.13)", icon: "hourglass_top", note: "در حال پیگیری" },
				{ label: "ارجاعات معوق", value: this.stats.overdue, color: "#DC2626", tintBg: "rgba(220,38,38,.13)", icon: "running_with_errors", note: "نیازمند رسیدگی فوری" },
				{ label: "نامه‌های امروز", value: this.stats.today, color: "#16A34A", tintBg: "rgba(22,163,74,.13)", icon: "mark_email_unread", note: "دریافت‌شده امروز" },
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
				] },
				{ title: "سایر", items: [
					{ key: "drafts", label: "پیش‌نویس‌ها", icon: "draft", scope: "drafts", count: c.drafts },
					{ key: "private", label: "خصوصی", icon: "lock", scope: "visibility", visibility: "private" },
					{ key: "public", label: "عمومی", icon: "public", scope: "visibility", visibility: "public" },
				] },
			];
		},
		folderTitle() {
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
		toggleTheme() {
			this.theme = this.theme === "dark" ? "light" : "dark";
			localStorage.setItem("oa_theme", this.theme);
		},
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
			if (r.outcome === "Approved" || r.status === "Actioned") return { background: "rgba(22,163,74,.15)", color: "#16A34A" };
			if (r.outcome === "Rejected") return { background: "rgba(220,38,38,.13)", color: "#DC2626" };
			return { background: "var(--primary-container)", color: "var(--on-primary-container)" };
		},
		dotIcon(r) {
			if (r.outcome === "Approved" || r.status === "Actioned") return "check";
			if (r.outcome === "Rejected") return "close";
			return "forward_to_inbox";
		},
		navStyle(key) {
			return this.view === key ? "background:var(--primary-container);color:var(--on-primary-container)" : "background:transparent;color:var(--on-variant)";
		},
		route(doctype) {
			frappe.set_route("List", doctype);
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
				const all = await frappe.xcall(API + "get_inbox_items", { folder: "all" });
				this.pending = all.slice(0, 5);
			} catch (e) { this.pending = []; }
		},
		goDashboard() { this.view = "dashboard"; this.loadDashboard(); },
		goInbox() { this.view = "inbox"; this.loadCounts(); this.loadFolder(); },
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
				else if (f.scope === "outbox") this.items = await frappe.xcall(API + "get_outbox_items", { state: f.state });
				else if (f.scope === "drafts") this.items = (await frappe.xcall(API + "get_drafts")).map((d) => ({ ...d, reference_name: d.name, reference_title: d.subject, status: "Draft" }));
				else if (f.scope === "visibility") this.items = (await frappe.xcall(API + "get_letters_by_visibility", { visibility: f.visibility })).map((d) => ({ ...d, reference_name: d.name, reference_title: d.subject }));
			} catch (e) { this.items = []; }
			finally { this.loading = false; }
		},
		async openItem(L) {
			if (this.scope === "inbox" && L.status === "Unseen") {
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
			this.composeLetter = letter || null;
			this.composeOpen = true;
		},
		onCreated(res) {
			this.composeOpen = false;
			if (res && res.refer && res.name) {
				this.forwardDialog("Automation Letter", res.name, null);
			}
			this.loadCounts();
			if (this.view === "inbox") this.loadFolder();
			if (this.view === "dashboard") this.loadDashboard();
		},
		async decideCur(kind) {
			// Act on the current user's open referral for this letter.
			const mine = (this.cur.referrals || []).find((r) => r.recipient === this.meEmail && ["Unseen", "Seen"].includes(r.status));
			if (!mine) { frappe.msgprint("ارجاع بازی برای شما روی این نامه وجود ندارد."); return; }
			const method = kind === "approve" ? "approve_referral" : "reject_referral";
			const d = new frappe.ui.Dialog({
				title: kind === "approve" ? "تأیید ارجاع" : "رد ارجاع",
				fields: [{ label: "یادداشت", fieldname: "note", fieldtype: "Small Text" }],
				primary_action_label: kind === "approve" ? "تأیید" : "رد",
				primary_action: async (v) => {
					await frappe.xcall(REF + method, { referral: mine.name, note: v.note });
					d.hide();
					frappe.show_alert({ message: kind === "approve" ? "تأیید شد" : "رد شد", indicator: kind === "approve" ? "green" : "red" });
					this.openLetter(this.cur.name);
				},
			});
			d.show();
		},
		referCur() {
			const mine = (this.cur.referrals || []).find((r) => r.recipient === this.meEmail && ["Unseen", "Seen"].includes(r.status));
			this.forwardDialog("Automation Letter", this.cur.name, mine ? mine.name : null);
		},
		forwardDialog(doctype, name, parent) {
			const FA = { دستور: "Order", پیگیری: "Follow-up", اقدام: "Action", استحضار: "Notification", اطلاع: "Info" };
			const d = new frappe.ui.Dialog({
				title: "ارجاع (Erja)",
				fields: [
					{ label: "گیرنده", fieldname: "recipient", fieldtype: "Link", options: "User", reqd: 1 },
					{ label: "نوع ارجاع", fieldname: "referral_type", fieldtype: "Select", options: Object.keys(FA).join("\n"), default: "اقدام" },
					{ label: "هامش‌نویسی", fieldname: "instruction", fieldtype: "Small Text" },
					{ label: "پیوست", fieldname: "attachment", fieldtype: "Attach" },
				],
				primary_action_label: "ارجاع",
				primary_action: async (v) => {
					await frappe.xcall(REF + "forward_document", {
						doc_type: doctype,
						doc_name: name,
						recipient: v.recipient,
						referral_type: FA[v.referral_type] || "Action",
						instruction: v.instruction,
						attachment: v.attachment,
						parent_referral: parent,
					});
					d.hide();
					frappe.show_alert({ message: "ارجاع شد", indicator: "green" });
					if (this.view === "letter") this.openLetter(name); else this.loadFolder();
					this.loadCounts();
				},
			});
			d.show();
		},
	},
};
</script>
