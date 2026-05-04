---
name: Luminous Creative
colors:
  surface: '#f9f9f9'
  surface-dim: '#dadada'
  surface-bright: '#f9f9f9'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f3f3f4'
  surface-container: '#eeeeee'
  surface-container-high: '#e8e8e8'
  surface-container-highest: '#e2e2e2'
  on-surface: '#1a1c1c'
  on-surface-variant: '#494455'
  inverse-surface: '#2f3131'
  inverse-on-surface: '#f0f1f1'
  outline: '#7a7487'
  outline-variant: '#cac3d8'
  surface-tint: '#6833ea'
  primary: '#632ce5'
  on-primary: '#ffffff'
  primary-container: '#7c4dff'
  on-primary-container: '#fcf6ff'
  inverse-primary: '#cdbdff'
  secondary: '#5d5e63'
  on-secondary: '#ffffff'
  secondary-container: '#dfdfe4'
  on-secondary-container: '#616267'
  tertiary: '#595a5c'
  on-tertiary: '#ffffff'
  tertiary-container: '#727275'
  on-tertiary-container: '#faf8fb'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#e8deff'
  primary-fixed-dim: '#cdbdff'
  on-primary-fixed: '#20005f'
  on-primary-fixed-variant: '#4f00d0'
  secondary-fixed: '#e2e2e7'
  secondary-fixed-dim: '#c6c6cb'
  on-secondary-fixed: '#1a1c1f'
  on-secondary-fixed-variant: '#45474b'
  tertiary-fixed: '#e3e2e5'
  tertiary-fixed-dim: '#c7c6c9'
  on-tertiary-fixed: '#1b1b1e'
  on-tertiary-fixed-variant: '#464649'
  background: '#f9f9f9'
  on-background: '#1a1c1c'
  surface-variant: '#e2e2e2'
typography:
  display:
    fontFamily: Manrope
    fontSize: 34px
    fontWeight: '700'
    lineHeight: 41px
    letterSpacing: -0.02em
  h1:
    fontFamily: Manrope
    fontSize: 28px
    fontWeight: '600'
    lineHeight: 34px
    letterSpacing: -0.01em
  h2:
    fontFamily: Manrope
    fontSize: 22px
    fontWeight: '600'
    lineHeight: 28px
  body-lg:
    fontFamily: Inter
    fontSize: 17px
    fontWeight: '400'
    lineHeight: 24px
  body-md:
    fontFamily: Inter
    fontSize: 15px
    fontWeight: '400'
    lineHeight: 21px
  label-caps:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.05em
  caption:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '500'
    lineHeight: 18px
rounded:
  sm: 0.5rem
  DEFAULT: 1rem
  md: 1.5rem
  lg: 2rem
  xl: 3rem
  full: 9999px
spacing:
  margin-main: 20px
  gutter-grid: 12px
  stack-sm: 8px
  stack-md: 16px
  stack-lg: 24px
  safe-area-bottom: 34px
---

## Brand & Style

The brand personality is rooted in the "Quiet Luxury" of digital tools—sophisticated, unobtrusive, and highly functional. It targets creative professionals and hobbyists who value a distraction-free environment that prioritizes their artwork over the interface.

The design style is **Modern iOS Minimalism** infused with **Glassmorphism**. It leverages high-quality white space to create a sense of breathing room, ensuring the AI-generated imagery remains the focal point. The emotional response should be one of "effortless power," where the UI feels like a high-end physical gallery or a premium stationery set. It strictly avoids the "gamer" aesthetic typical of AI tools, opting instead for an editorial, Apple-ecosystem aesthetic.

## Colors

The palette is restrained to maintain a premium feel. The primary accent (#7C4DFF) is used sparingly for actionable elements and brand moments.

- **Primary:** A refined blue-purple used for primary buttons, active states, and selection indicators.
- **Secondary/Surface:** Off-whites and light greys used to differentiate layers without creating harsh contrast.
- **Background:** Pure White (#FFFFFF) for cards and modals, against a slightly tinted System Background (#F9F9FB) to provide depth.
- **Translucency:** Backgrounds for navigation bars and floating panels utilize a 70-80% opacity white with a heavy backdrop-blur (20px+) to emulate frosted glass.

## Typography

This design system uses a dual-font approach to balance character with utility. **Manrope** is used for headlines to provide a modern, slightly geometric "designer" feel. **Inter** is used for all body text, inputs, and labels to ensure maximum legibility at small sizes, maintaining the systematic iOS feel.

Large titles should use a "tight" letter spacing to feel more integrated. All secondary text should use the tertiary color (#636366) to establish a clear information hierarchy.

## Layout & Spacing

The layout follows a **Fluid Grid** model optimized for mobile viewpoints. It utilizes a standard 16pt or 20pt margin on the horizontal axis.

- **Vertical Rhythm:** Elements are grouped using a 4px-base scale (8, 16, 24, 32).
- **Margins:** A consistent 20px margin is applied to the left and right of the screen for primary content.
- **Padding:** Generous internal padding within cards (min 20px) ensures content never feels cramped, reinforcing the premium aesthetic.

## Elevation & Depth

Depth is conveyed through **Glassmorphism** and **Ambient Shadows** rather than stark borders.

1.  **Base Layer:** The system background (#F9F9FB).
2.  **Card Layer:** Pure white surfaces with a "Floating" shadow (0px Y, 10px Blur, 0.04 Opacity Black).
3.  **Interactive Layer:** Primary buttons use a subtle tinted shadow of the primary color to suggest "glow" without being neon.
4.  **Overlay Layer:** Modals and bottom sheets use a heavy backdrop-blur (Material Ultra Thin) to allow the content underneath to bleed through softly, maintaining context.

## Shapes

The shape language is defined by "Squircle" mathematics and high radii.

- **Cards:** Use a minimum of 24px to 32px corner radius to feel soft and approachable.
- **Buttons:** Fully rounded (pill-shaped) to distinguish them clearly from content cards.
- **Inputs:** A consistent 16px radius.
- **Icons:** Use 1.5pt to 2pt linear stroke weights with rounded caps and joins to match the soft UI geometry.

## Components

- **Primary Buttons:** Pill-shaped, #7C4DFF background with white text. No gradients.
- **Secondary Buttons:** Translucent #7C4DFF at 10% opacity with #7C4DFF text.
- **AI Image Cards:** 32px corner radius, overflowing image content, with a frosted glass "Prompt Label" overlaying the bottom edge.
- **Prompt Input:** A large, multi-line text area with a subtle 1px border (#E5E5EA) that turns into the primary accent color on focus.
- **Segmented Controls:** A pill-shaped track with a white physical "slider" that has a soft shadow.
- **Creation Chips:** Small, pill-shaped tags used for art styles (e.g., "Impressionist," "3D Render") using a #F2F2F7 background and #636366 text.
- **Bottom Navigation:** A clear frosted-glass bar with simple 24px linear icons; the active state is indicated by a subtle primary color tint and a 4px dot below the icon.
