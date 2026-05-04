<script setup lang="ts">
import { onLaunch } from '@dcloudio/uni-app'

const appReady = true

onLaunch(() => {
  // #ifdef H5
  if (window.location.hash === '#/' || window.location.hash === '') {
    uni.reLaunch({ url: '/pages/create/index' })
  }
  // #endif
})
</script>

<template>
  <view v-if="appReady"></view>
</template>

<style>
page {
  min-height: 100%;
  background: #f4f5f7;
  color: #1a1c1c;
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "PingFang SC", Inter, "Segoe UI", sans-serif;
}

/* #ifdef H5 */
html,
body {
  background:
    radial-gradient(circle at 50% -12%, rgba(124, 77, 255, 0.12), transparent 32%),
    radial-gradient(circle at 88% 18%, rgba(111, 170, 255, 0.1), transparent 28%),
    linear-gradient(180deg, #f5f6f8 0%, #e9ebf0 100%);
}

uni-app,
uni-page,
uni-page-body {
  max-width: 430px;
  min-height: 100vh;
  margin: 0 auto;
  background: #f5f5f7;
}

uni-page {
  box-shadow: 0 28px 90px rgba(18, 23, 35, 0.16);
  overflow: hidden;
}

uni-tabbar {
  left: 50% !important;
  width: calc(100% - 56px) !important;
  max-width: 374px !important;
  transform: translateX(-50%);
  bottom: 0 !important;
  overflow: visible !important;
  background: transparent !important;
}

uni-tabbar .uni-tabbar {
  position: relative !important;
  height: 54px !important;
  padding: 4px 15px 4px !important;
  margin-bottom: env(safe-area-inset-bottom);
  overflow: hidden !important;
  isolation: isolate;
  background:
    radial-gradient(120% 86% at 18% 0%, rgba(255, 255, 255, 0.98), rgba(255, 255, 255, 0.58) 46%, rgba(255, 255, 255, 0.32) 72%),
    radial-gradient(92% 120% at 94% 100%, rgba(124, 77, 255, 0.16), rgba(255, 255, 255, 0) 62%),
    linear-gradient(135deg, rgba(255, 255, 255, 0.78), rgba(245, 247, 252, 0.64) 54%, rgba(236, 239, 248, 0.7)),
    rgba(250, 250, 252, 0.76) !important;
  backdrop-filter: blur(46px) saturate(245%) contrast(112%);
  -webkit-backdrop-filter: blur(46px) saturate(245%) contrast(112%);
  border: 1px solid rgba(255, 255, 255, 0.78) !important;
  border-radius: 999px !important;
  box-shadow:
    0 18px 42px rgba(20, 24, 34, 0.16),
    0 5px 14px rgba(20, 24, 34, 0.09),
    inset 0 1px 0 rgba(255, 255, 255, 0.96),
    inset 0 -1px 0 rgba(115, 119, 134, 0.12),
    inset 0 0 22px rgba(255, 255, 255, 0.32) !important;
}

uni-tabbar .uni-tabbar::before {
  content: "";
  position: absolute;
  inset: 1px;
  z-index: -1;
  border-radius: inherit;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.76), rgba(255, 255, 255, 0.18) 46%, rgba(255, 255, 255, 0.08)),
    radial-gradient(76% 78% at 50% 0%, rgba(255, 255, 255, 0.82), transparent 62%),
    radial-gradient(92% 110% at 96% 100%, rgba(124, 77, 255, 0.1), transparent 58%);
  pointer-events: none;
}

uni-tabbar .uni-tabbar::after {
  content: "";
  position: absolute;
  left: 22px;
  right: 22px;
  top: 1px;
  height: 1px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.98);
  pointer-events: none;
}

uni-tabbar .uni-tabbar__item {
  background: transparent !important;
  border: 0 !important;
  box-shadow: none !important;
  border-radius: 999px !important;
  transition: transform 160ms ease, background-color 160ms ease;
}

uni-tabbar .uni-tabbar__item:active {
  transform: scale(0.97);
  background: rgba(255, 255, 255, 0.46) !important;
}

uni-tabbar .uni-tabbar__icon {
  width: 20.5px !important;
  height: 20.5px !important;
  margin-bottom: 1px !important;
  filter: saturate(125%) contrast(112%) drop-shadow(0 1px 1px rgba(255, 255, 255, 0.72));
}

uni-tabbar .uni-tabbar__label {
  font-family: Manrope, Inter, sans-serif !important;
  font-size: 10.1px !important;
  line-height: 12.5px !important;
  font-weight: 620 !important;
  text-shadow: 0 1px 1px rgba(255, 255, 255, 0.76);
}
/* #endif */

view,
scroll-view,
text,
input,
textarea,
button,
image {
  box-sizing: border-box;
}

button {
  padding: 0;
  margin: 0;
  background: transparent;
  border: 0;
  line-height: inherit;
}

button::after {
  border: 0;
}

image {
  display: block;
}

.mio-page {
  min-height: 100vh;
  max-width: 430px;
  margin: 0 auto;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.84) 0%, rgba(245, 245, 247, 0.96) 42%, #f5f5f7 100%);
  color: #1a1c1c;
  padding-left: 20px;
  padding-right: 20px;
  padding-bottom: calc(92px + env(safe-area-inset-bottom));
}

.mio-page.with-top {
  padding-top: calc(24px + env(safe-area-inset-top));
}

.mio-topbar {
  position: fixed;
  top: 0;
  left: 50%;
  right: auto;
  width: 100%;
  max-width: 430px;
  transform: translateX(-50%);
  z-index: 50;
  height: calc(64px + env(safe-area-inset-top));
  padding: env(safe-area-inset-top) 20px 0;
  background: var(--liquid-bg), rgba(250, 250, 252, 0.3);
  backdrop-filter: var(--liquid-filter);
  -webkit-backdrop-filter: var(--liquid-filter);
  border-bottom: 1px solid rgba(255, 255, 255, 0.66);
  box-shadow:
    0 14px 34px rgba(26, 31, 44, 0.08),
    inset 0 1px 0 rgba(255, 255, 255, 0.9),
    inset 0 -1px 0 rgba(120, 124, 140, 0.08);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.mio-title {
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "PingFang SC", Manrope, Inter, sans-serif;
  font-size: 26px;
  line-height: 31px;
  font-weight: 700;
  letter-spacing: 0;
}

.mio-h2 {
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "PingFang SC", Manrope, Inter, sans-serif;
  font-size: 20px;
  line-height: 26px;
  font-weight: 600;
}

.mio-body {
  font-size: 14px;
  line-height: 20px;
}

.mio-caption {
  font-size: 13px;
  line-height: 18px;
  font-weight: 500;
}

.mio-muted {
  color: #6e6e73;
}

.mio-primary {
  color: #7c4dff;
}

:root,
page {
  --liquid-bg:
    radial-gradient(120% 85% at 18% 0%, rgba(255, 255, 255, 0.92), rgba(255, 255, 255, 0.28) 42%, rgba(255, 255, 255, 0) 68%),
    radial-gradient(85% 100% at 92% 100%, rgba(124, 77, 255, 0.18), rgba(255, 255, 255, 0) 58%),
    linear-gradient(135deg, rgba(255, 255, 255, 0.58), rgba(255, 255, 255, 0.22) 44%, rgba(242, 244, 252, 0.38));
  --liquid-bg-soft:
    radial-gradient(120% 85% at 18% 0%, rgba(255, 255, 255, 0.84), rgba(255, 255, 255, 0.22) 42%, rgba(255, 255, 255, 0) 68%),
    radial-gradient(85% 100% at 92% 100%, rgba(124, 77, 255, 0.13), rgba(255, 255, 255, 0) 58%),
    linear-gradient(135deg, rgba(255, 255, 255, 0.48), rgba(255, 255, 255, 0.18) 44%, rgba(242, 244, 252, 0.3));
  --liquid-border: rgba(255, 255, 255, 0.66);
  --liquid-highlight: rgba(255, 255, 255, 0.92);
  --liquid-shadow:
    0 20px 48px rgba(20, 24, 34, 0.11),
    0 5px 14px rgba(20, 24, 34, 0.06),
    inset 0 1px 0 rgba(255, 255, 255, 0.9),
    inset 0 -1px 0 rgba(120, 124, 140, 0.08);
  --liquid-filter: blur(34px) saturate(215%) contrast(106%);
}

.liquid-glass,
.glass-card,
.mio-card {
  position: relative;
  isolation: isolate;
  overflow: hidden;
  background: var(--liquid-bg), rgba(250, 250, 252, 0.32);
  backdrop-filter: var(--liquid-filter);
  -webkit-backdrop-filter: var(--liquid-filter);
  border: 1px solid var(--liquid-border);
  box-shadow: var(--liquid-shadow);
}

.liquid-glass::before,
.glass-card::before,
.mio-card::before {
  content: "";
  position: absolute;
  left: 12px;
  right: 12px;
  top: 1px;
  height: 1px;
  border-radius: 999px;
  background: var(--liquid-highlight);
  pointer-events: none;
  z-index: 1;
}

.mio-card {
  border-radius: 18px;
}

.pill {
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.primary-button {
  min-height: 48px;
  padding: 0 20px;
  border-radius: 999px;
  background: #7c4dff;
  color: #fff;
  font-size: 15px;
  font-weight: 600;
  box-shadow: 0 12px 24px rgba(124, 77, 255, 0.22), inset 0 1px 0 rgba(255, 255, 255, 0.24);
  display: flex;
  align-items: center;
  justify-content: center;
}

.secondary-chip {
  padding: 7px 14px;
  border-radius: 999px;
  background: var(--liquid-bg-soft), rgba(250, 250, 252, 0.26);
  color: #5f6066;
  border: 1px solid rgba(255, 255, 255, 0.58);
  font-size: 13px;
  line-height: 19px;
  white-space: nowrap;
  box-shadow:
    0 9px 20px rgba(29, 34, 47, 0.06),
    inset 0 1px 0 rgba(255, 255, 255, 0.82),
    inset 0 -1px 0 rgba(120, 124, 140, 0.06);
  backdrop-filter: blur(22px) saturate(190%) contrast(104%);
  -webkit-backdrop-filter: blur(22px) saturate(190%) contrast(104%);
}

.icon-button {
  width: 36px;
  height: 36px;
  border-radius: 999px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #72727a;
  background: var(--liquid-bg-soft), rgba(250, 250, 252, 0.24);
  border: 1px solid rgba(255, 255, 255, 0.58);
  box-shadow:
    0 10px 22px rgba(29, 34, 47, 0.07),
    inset 0 1px 0 rgba(255, 255, 255, 0.82),
    inset 0 -1px 0 rgba(120, 124, 140, 0.06);
  backdrop-filter: blur(24px) saturate(200%) contrast(104%);
  -webkit-backdrop-filter: blur(24px) saturate(200%) contrast(104%);
  transition: opacity 180ms ease, transform 180ms ease, background 180ms ease;
}

.reference-insert {
  position: relative;
  width: 38px;
  height: 38px;
  flex-shrink: 0;
  background: var(--liquid-bg-soft), rgba(250, 250, 252, 0.28);
  border: 1px solid rgba(255, 255, 255, 0.64);
  box-shadow:
    0 12px 28px rgba(31, 35, 48, 0.09),
    inset 0 1px 0 rgba(255, 255, 255, 0.9),
    inset 0 -1px 0 rgba(124, 77, 255, 0.06);
  backdrop-filter: blur(26px) saturate(205%) contrast(104%);
  -webkit-backdrop-filter: blur(26px) saturate(205%) contrast(104%);
}

.reference-insert.active {
  background: linear-gradient(180deg, #9170ff 0%, #7045ee 100%);
  border-color: rgba(255, 255, 255, 0.62);
  box-shadow:
    0 12px 26px rgba(124, 77, 255, 0.22),
    inset 0 1px 0 rgba(255, 255, 255, 0.36);
}

.reference-symbol {
  position: relative;
  width: 25px;
  height: 25px;
}

.reference-symbol-frame {
  position: absolute;
  left: 1px;
  top: 2px;
  width: 20px;
  height: 18px;
  border-radius: 7px;
  background: #f3eeff;
  border: 1.5px solid rgba(124, 77, 255, 0.78);
  overflow: hidden;
}

.reference-symbol-dot {
  position: absolute;
  left: 4px;
  top: 4px;
  width: 4px;
  height: 4px;
  border-radius: 999px;
  background: #7c4dff;
}

.reference-symbol-hill {
  position: absolute;
  left: 3px;
  right: 3px;
  bottom: 2px;
  height: 8px;
  border-radius: 8px 8px 4px 4px;
  background: linear-gradient(135deg, rgba(124, 77, 255, 0.18), rgba(124, 77, 255, 0.36));
  transform: skewX(-10deg);
}

.reference-symbol-badge {
  position: absolute;
  right: 0;
  bottom: 0;
  width: 13px;
  height: 13px;
  border-radius: 999px;
  background: #7c4dff;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  line-height: 13px;
  font-weight: 700;
  box-shadow: 0 0 0 2px rgba(255, 255, 255, 0.9);
}

.reference-symbol.active .reference-symbol-frame {
  background: rgba(255, 255, 255, 0.24);
  border-color: rgba(255, 255, 255, 0.82);
}

.reference-symbol.active .reference-symbol-dot,
.reference-symbol.active .reference-symbol-hill {
  background: rgba(255, 255, 255, 0.86);
}

.reference-symbol.active .reference-symbol-badge {
  background: #fff;
  color: #6d43ee;
  box-shadow: 0 0 0 2px rgba(124, 77, 255, 0.18);
}

.floating-actions {
  position: fixed;
  top: calc(12px + env(safe-area-inset-top));
  left: 50vw;
  right: auto;
  z-index: 90;
  width: calc(100vw - 32px);
  max-width: 398px;
  transform: translateX(-50%);
  height: 38px;
  display: block;
  pointer-events: none;
}

.floating-actions > .float-button {
  position: absolute;
  top: 0;
  left: 0;
}

.floating-actions > .more-wrap {
  position: absolute;
  top: 0;
  right: 0;
}

.float-button {
  pointer-events: auto;
  width: 38px;
  height: 38px;
  border-radius: 999px;
  color: #202124;
  overflow: hidden;
  isolation: isolate;
  background: var(--liquid-bg-soft), rgba(250, 250, 252, 0.28);
  border: 1px solid rgba(255, 255, 255, 0.62);
  box-shadow:
    0 14px 32px rgba(20, 24, 34, 0.12),
    inset 0 1px 0 rgba(255, 255, 255, 0.9),
    inset 0 -1px 0 rgba(120, 124, 140, 0.08);
  backdrop-filter: blur(30px) saturate(210%) contrast(104%);
  -webkit-backdrop-filter: blur(30px) saturate(210%) contrast(104%);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: opacity 180ms ease, transform 180ms ease, background 180ms ease;
}

.float-button::before {
  content: "";
  position: absolute;
  left: 9px;
  right: 9px;
  top: 1px;
  height: 1px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.9);
  pointer-events: none;
}

.float-button:active {
  opacity: 0.78;
  transform: scale(0.94);
}

.more-wrap {
  position: relative;
  pointer-events: auto;
}

.more-dots {
  display: block;
  color: #2b2c31;
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", sans-serif;
  font-size: 18px;
  line-height: 18px;
  font-weight: 700;
  letter-spacing: 1.5px;
  transform: translateY(-1px);
}

.floating-menu {
  position: absolute;
  top: 46px;
  right: 0;
  min-width: 142px;
  padding: 6px;
  border-radius: 18px;
  overflow: hidden;
  isolation: isolate;
  background: var(--liquid-bg), rgba(250, 250, 252, 0.34);
  border: 1px solid rgba(255, 255, 255, 0.66);
  box-shadow:
    0 22px 52px rgba(29, 34, 47, 0.16),
    inset 0 1px 0 rgba(255, 255, 255, 0.9),
    inset 0 -1px 0 rgba(120, 124, 140, 0.08);
  backdrop-filter: blur(38px) saturate(220%) contrast(106%);
  -webkit-backdrop-filter: blur(38px) saturate(220%) contrast(106%);
}

.floating-menu-item {
  width: 100%;
  min-height: 36px;
  padding: 0 12px;
  border-radius: 12px;
  color: #1d1d1f;
  font-size: 13px;
  font-weight: 560;
  text-align: left;
  display: flex;
  align-items: center;
}

.floating-menu-item:active {
  background:
    radial-gradient(120% 88% at 18% 0%, rgba(255, 255, 255, 0.78), rgba(255, 255, 255, 0.18) 54%, rgba(255, 255, 255, 0) 72%),
    rgba(255, 255, 255, 0.2);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.78),
    inset 0 -1px 0 rgba(120, 124, 140, 0.06);
}

.floating-menu-item.danger {
  color: #d13b45;
}

.icon-button:active,
.primary-button:active,
.secondary-chip:active {
  opacity: 0.78;
  transform: scale(0.96);
}

.simple-icon {
  font-size: 20px;
  line-height: 1;
  font-weight: 600;
  color: currentColor;
}

.svg-icon {
  width: 22px;
  height: 22px;
  display: block;
}

.svg-icon.sm {
  width: 16px;
  height: 16px;
}

.svg-icon.lg {
  width: 26px;
  height: 26px;
}

.nav-symbol {
  display: block;
  color: currentColor;
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", sans-serif;
  font-size: 28px;
  line-height: 24px;
  font-weight: 400;
}

.line-icon {
  width: 22px;
  height: 22px;
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: currentColor;
}

.line-icon::before,
.line-icon::after,
.line-icon .line {
  content: "";
  position: absolute;
  display: block;
  box-sizing: border-box;
}

.line-icon.menu .line,
.line-icon.menu::before,
.line-icon.menu::after {
  left: 2px;
  width: 18px;
  height: 2px;
  border-radius: 999px;
  background: currentColor;
}

.line-icon.menu::before { top: 5px; }
.line-icon.menu .line { top: 10px; }
.line-icon.menu::after { top: 15px; }

.line-icon.history {
  border: 2px solid currentColor;
  border-radius: 999px;
}

.line-icon.history::before {
  width: 2px;
  height: 6px;
  border-radius: 999px;
  background: currentColor;
  left: 10px;
  top: 5px;
}

.line-icon.history::after {
  width: 6px;
  height: 2px;
  border-radius: 999px;
  background: currentColor;
  left: 10px;
  top: 11px;
  transform: rotate(24deg);
  transform-origin: left center;
}

.line-icon.plus::before,
.line-icon.plus::after {
  width: 16px;
  height: 2px;
  border-radius: 999px;
  background: currentColor;
}

.line-icon.plus::after {
  transform: rotate(90deg);
}

.line-icon.back::before {
  width: 12px;
  height: 12px;
  border-left: 2px solid currentColor;
  border-bottom: 2px solid currentColor;
  transform: rotate(45deg);
  left: 7px;
  top: 5px;
}

.line-icon.chevron::before {
  width: 9px;
  height: 9px;
  border-right: 2px solid currentColor;
  border-top: 2px solid currentColor;
  transform: rotate(45deg);
}

.line-icon.send::before {
  width: 0;
  height: 0;
  border-top: 8px solid transparent;
  border-bottom: 8px solid transparent;
  border-left: 13px solid currentColor;
  margin-left: 3px;
}

.line-icon.search::before {
  width: 13px;
  height: 13px;
  border: 2px solid currentColor;
  border-radius: 999px;
  left: 2px;
  top: 2px;
}

.line-icon.search::after {
  width: 9px;
  height: 2px;
  border-radius: 999px;
  background: currentColor;
  transform: rotate(45deg);
  right: 2px;
  bottom: 4px;
}

.line-icon.spark::before {
  width: 16px;
  height: 16px;
  background: currentColor;
  clip-path: polygon(50% 0%, 60% 38%, 100% 50%, 60% 62%, 50% 100%, 40% 62%, 0% 50%, 40% 38%);
}

.line-icon.close::before,
.line-icon.close::after {
  width: 17px;
  height: 2px;
  border-radius: 999px;
  background: currentColor;
  transform: rotate(45deg);
}

.line-icon.close::after {
  transform: rotate(-45deg);
}

.line-icon.settings::before {
  width: 17px;
  height: 17px;
  border: 2px solid currentColor;
  border-radius: 999px;
}

.line-icon.settings::after {
  width: 5px;
  height: 5px;
  border-radius: 999px;
  background: currentColor;
}

.status-dot {
  width: 7px;
  height: 7px;
  border-radius: 999px;
  background: #7c4dff;
}

.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
