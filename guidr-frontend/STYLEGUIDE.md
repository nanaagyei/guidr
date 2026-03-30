# Guidr Style Guide

This document defines the design system and styling guidelines for Guidr.

## Color Palette

Guidr uses a minimalistic, clean color palette for a modern and professional feel.

### Primary Colors
- **Background:** `#FAFAFA` - Off-white background for main content
- **Card:** `#FFFFFF` - White for card backgrounds
- **Sidebar:** `#1F2937` - Dark gray for sidebar background
- **Primary:** `#3B82F6` - Blue accent for primary actions and highlights
- **Text:** `#111827` - Dark text for primary content

### Secondary Colors
- **Sidebar Hover:** `#374151` - Hover state for sidebar elements
- **Primary Hover:** `#2563EB` - Hover state for primary buttons
- **Text Secondary:** `#6B7280` - Secondary text color
- **Border:** `#E5E7EB` - Light borders
- **Muted:** `#F3F4F6` - Muted backgrounds

### Usage Guidelines
- **Primary actions:** Use Primary (`bg-primary text-white`)
- **Secondary actions:** Use Gray (`bg-gray-700 text-white`)
- **Backgrounds:** Use Background for main content, Card for elevated surfaces
- **Text:** Use Text for body text, Text Secondary for less important content
- **Sidebar:** Use Sidebar for sidebar background with white/gray-300 text
- **Hover states:** Use Primary Hover for primary buttons, Sidebar Hover for sidebar elements

## Typography

### Font Family
- **Base font:** Inter, system-ui, -apple-system, sans-serif
- Clean, modern sans-serif for excellent readability

### Heading Hierarchy
- **H1:** `text-3xl font-semibold` (2.5rem, 600 weight) - Page titles
- **H2:** `text-2xl font-semibold` (2rem, 600 weight) - Section headers
- **H3:** `text-xl font-semibold` (1.5rem, 600 weight) - Subsection headers
- **Body:** `text-base` (1rem, 400 weight) - Default text
- **Small:** `text-sm` (0.875rem) - Secondary text, captions

### Text Colors
- **Headings:** Text (`text-text`) for primary headings
- **Body:** Text (`text-text`) for body content
- **Secondary:** Text Secondary (`text-textSecondary`) for less important text
- **Sidebar:** White/Gray-300 (`text-white` or `text-gray-300`) for sidebar text

## Spacing

Use Tailwind's spacing scale consistently:
- **Major layout gaps:** `gap-8` (2rem)
- **Section spacing:** `space-y-6` (1.5rem)
- **Card padding:** `p-6` (1.5rem)
- **Button padding:** `px-6 py-3` (horizontal 1.5rem, vertical 0.75rem)

## Components

### Buttons

#### Primary Button
```tsx
className="px-6 py-3 bg-primary text-white font-semibold rounded-lg hover:bg-primaryHover transition"
```
- Use for main actions (Get Started, Submit, Save)
- Primary blue background with white text
- Rounded corners (`rounded-lg`)
- Smooth hover transition

#### Secondary Button
```tsx
className="px-6 py-3 bg-gray-700 text-white font-semibold rounded-lg hover:bg-gray-800 transition"
```
- Use for secondary actions
- Gray background with white text

### Cards

```tsx
className="bg-card rounded-xl p-6 shadow-sm hover:shadow-md transition border border-border"
```
- White card background
- Rounded corners (`rounded-xl` for softer feel)
- Subtle shadow that increases on hover
- Light border for definition
- Padding: `p-6`

### Layout

- **Sidebar width:** `w-64` (16rem)
- **Main content:** `flex-1` with `max-w-4xl mx-auto` for centered content
- **Container padding:** `p-8` for main content area

## Design Philosophy

Guidr aims to feel:
- **Clean and minimalistic** - Modern and uncluttered
- **Professional** - Trustworthy and polished
- **Approachable** - Easy to use and navigate
- **Consistent** - Cohesive design system throughout

### Key Principles
1. **Rounded corners** - Use `rounded-lg` or `rounded-xl` for modern feel
2. **Subtle shadows** - `shadow-sm` to `shadow-md` for depth without heaviness
3. **Smooth transitions** - Add `transition` class to interactive elements
4. **Comfortable spacing** - Generous whitespace for clarity
5. **Consistent colors** - Stick to the defined minimalistic palette
6. **White cards on off-white background** - Creates clear visual hierarchy

## Accessibility

- Ensure sufficient color contrast (WCAG AA minimum)
- Use semantic HTML elements
- Provide focus states for keyboard navigation
- Include alt text for images
- Test with screen readers

