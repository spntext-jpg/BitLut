# August v3 — Dark Workbench

August v3 — каноническая дизайн-система Giftomat. Её визуальная модель: **светлый Canvas + глубокие Navy work surfaces + Lime как заполненный action/brand accent + Purple как focus/secondary interaction accent + белые controls**.

Система должна ощущаться как современный профессиональный media workstation, а не как generic SaaS dashboard: крупные поверхности, ясная иерархия, мало декоративных рамок, высокая контрастность и один выразительный брендовый акцент.

## 1. Основные принципы

1. **Dark Workbench, Light Controls.** Зона работы с медиа тёмная; настройки и формы находятся на белых Surface.
2. **Lime — поверхность, а не текст на белом.** Lime используется для primary CTA, compact labels, progress и отдельных brand moments. На Lime всегда Ink-текст.
3. **Purple — interaction detail.** Purple отвечает за focus ring, secondary selection, links и точечные interactive cues. Он не конкурирует с Lime за роль primary CTA.
4. **Navy — архитектурный якорь.** Sidebar, media workbench и dark hero/header используют один Navy family.
5. **White active navigation.** Текущий инструмент в Navy sidebar — белая Surface-card с Ink-текстом и Lime icon tile.
6. **Контраст важнее декоративности.** Нельзя использовать Lime как мелкий foreground-текст на Canvas/Surface: контраста недостаточно.
7. **Одна каноническая реализация.** `app/globals.css` — единственный CSS source of truth. Никаких versioned override layers и `!important`.

## 2. Цветовые токены

### 2.1 Core neutrals

| Token | Value | Назначение |
|---|---:|---|
| `--august-ink` | `#151728` | основной тёмный текст, Ink на Lime |
| `--august-ink-soft` | `#292C3E` | secondary dark text / dark detail |
| `--august-muted` | `#6F7385` | secondary text на светлых поверхностях |
| `--august-canvas` | `#F7F8FC` | общий Canvas приложения |
| `--august-surface` | `#FFFFFF` | controls, active nav, cards |
| `--august-soft` | `#F2F3F7` | secondary controls / fields |

### 2.2 Brand Lime

| Token | Value | Назначение |
|---|---:|---|
| `--august-lime` | `#DFFF6A` | primary CTA, chips, progress, active icon tile |
| `--august-lime-hover` | `#D2F650` | hover primary action |
| `--august-lime-active` | `#C3E93E` | pressed primary action |
| `--august-lime-ink` | `#151728` | обязательный foreground на Lime |

**Контракт Lime:**

- разрешён как filled background;
- разрешён как border/indicator на Navy;
- разрешён как foreground только на Navy/dark workbench, когда контраст достаточен;
- запрещён как обычный текст/icon foreground на White/Canvas;
- primary button = Lime background + Ink text, никогда White text.

### 2.3 Purple interaction

| Token | Value | Назначение |
|---|---:|---|
| `--august-purple` | `#6E5CF6` | focus, links, selection details |
| `--august-purple-dark` | `#5140DC` | pressed/strong purple detail |
| `--august-purple-soft` | `#EEEAFF` | soft selected/focus surfaces |

Purple не используется как primary CTA, если действие может быть выражено Lime.

### 2.4 Dark anchor

| Token | Value | Назначение |
|---|---:|---|
| `--august-navy` | `#151728` | sidebar, deepest workbench |
| `--august-navy-raised` | `#1C1E33` | dark hero / raised work surface |
| `--august-navy-soft` | `#24263D` | hover/pressed dark surface |
| `--august-dark-secondary` | `#B8BDCE` | secondary text на Navy |

## 3. Surface architecture

В одном viewport одновременно могут присутствовать четыре уровня:

1. **Canvas** — `#F7F8FC`, фон приложения с очень мягкими Lime/Purple ambient glows.
2. **Navy anchor** — sidebar.
3. **Dark Workbench** — canvas/media panel для исходников, preview и crop.
4. **White Control Surface** — настройки, results и secondary controls.

Не нужно превращать каждую секцию в отдельную карточку. Большая поверхность важнее набора мелких cards.

## 4. Sidebar

Sidebar всегда Navy и не зависит от OS dark mode.

### Inactive destination

- dark transparent/raised background;
- title: White;
- note: `--august-dark-secondary`;
- icon: muted light on dark;
- hover может подсвечивать icon Lime, но текст остаётся светлым.

### Active destination

- background: White Surface;
- title: Ink;
- note: Muted;
- icon tile: Lime;
- icon glyph: Ink;
- shadow короткий и плотный, без Purple glow.

### Pressed-state contract

Цвет текста должен быть явно определён и на `:active`:

- inactive pressed: White + Dark Secondary;
- active pressed: Ink + Muted;
- `-webkit-text-fill-color` должен совпадать с `color`, чтобы Safari/iOS не делал текст прозрачным во время tap/press.

Sidebar button text не является selectable content; `user-select` и touch-callout выключены.

## 5. Dark Workbench

`canvas-panel` — тёмная рабочая поверхность, а не белая glass-card.

- базовый фон: Navy → Navy Raised;
- допустим один очень слабый Purple glow;
- border: `--august-border-dark`;
- uploaded media располагается внутри dark preview stage;
- empty state тоже dark;
- drag-active: Lime border + мягкое Lime outer ring;
- toolbar actions: white/dark-glass controls.

Lime здесь может использоваться как hover label/border, потому что лежит на Navy и имеет достаточный контраст.

## 6. Control Panel и Dark Hero

`control-panel` — White Surface. Верхняя часть — dark hero/header.

### Header

- Navy/Navy Raised background;
- large White title;
- Dark Secondary description;
- Lime eyebrow chip с Ink text;
- Purple допускается только как очень мягкий ambient glow.

### Settings

- белый фон;
- labels: Muted/Ink;
- inputs: Soft Surface;
- value/output: Lime pill + Ink text;
- selected segmented option: Navy + White;
- focus: Purple ring.

### Footer

- White Surface;
- primary CTA: Lime + Ink;
- helper text: Muted.

## 7. Buttons

### Primary

- min height: 44 px, стандартно 48 px;
- background: Lime;
- text/icon: Ink;
- hover: Lime Hover;
- active: Lime Active + `scale(.98)`;
- focus-visible: Purple two-stage ring;
- disabled: opacity/reduced saturation, но текст остаётся читаемым.

### Download

То же визуальное семейство, что primary. Download не должен неожиданно становиться Purple.

### Secondary

На White:

- Soft/transparent background;
- Ink/Muted text;
- neutral border;
- hover может использовать очень лёгкий Purple tint.

На Dark Workbench:

- translucent white background;
- White text;
- dark border;
- hover увеличивает white alpha, но не меняет текст на Lime.

### Destructive

Danger остаётся отдельным semantic color. Lime и Purple не используются для destructive meaning.

## 8. Selection и form controls

- segmented active: Navy + White;
- crop aspect-ratio active: Lime + Ink;
- frame selection: Purple border/ring;
- PDF/select focus: Purple;
- checkbox native accent: Purple;
- range track: Navy → Purple;
- range thumb: Lime с Navy border;
- text selection: Purple soft, не Lime.

## 9. Typography

Основной шрифт — self-hosted Inter Variable.

- Display / hero: 800–900, tight negative tracking;
- section title: 750–850;
- body: 500–650;
- label/eyebrow: 800–900, uppercase, increased tracking;
- numeric output: tabular figures.

Иерархия создаётся масштабом и весом, а не множеством цветов.

## 10. Radius system

Радиус зависит от масштаба объекта:

- small controls: 10–14 px;
- cards/fields: 14–18 px;
- work surfaces/control panels: 20–24 px;
- large marketing/hero surfaces: 28–40 px;
- chips: pill (`999px`).

Не использовать pill для каждого control.

## 11. Shadows

Shadows нейтральные, основаны на Ink/Navy. Цветной glow допустим только:

- слабый Lime для primary action;
- слабый Purple для focus/ambient detail.

Запрещены большие neon glows и постоянный glassmorphism на каждой поверхности.

## 12. Motion

- стандартные transitions: 140–200 ms;
- navigation/drawer: до 280 ms;
- pressed scale: `0.98`;
- no gratuitous bouncing;
- `prefers-reduced-motion` обязателен.

## 13. Responsive behavior

Контрольные viewport'ы:

- 360×800;
- 780×900;
- 1100×900;
- 1440×1000.

Правила:

- mobile nav остаётся dark drawer;
- touch target минимум 44×44 px для основных действий;
- title/note sidebar не должны исчезать из-за press/active cascade;
- dark workbench и white controls сохраняют роли на всех breakpoints;
- при переходе в single-column порядок должен оставаться Workbench → Controls.

## 14. Accessibility

- focus-visible всегда Purple и заметен на White и Navy;
- White text на Navy;
- Ink text на Lime;
- Lime foreground на White запрещён;
- active sidebar White/Ink;
- muted text используется только для secondary information;
- состояние не должно сообщаться только цветом;
- disabled controls не должны становиться невидимыми.

## 15. PWA / browser chrome

- `theme_color`: Navy `#151728`;
- `background_color`: Canvas `#F7F8FC`;
- при существенном изменении app shell нужно увеличивать `CACHE_VERSION` service worker.

## 16. Implementation rules

1. `app/globals.css` — canonical implementation.
2. Никаких `!important`.
3. Никаких versioned CSS override blocks.
4. Никакого Tailwind toolchain без отдельного решения о миграции.
5. Не вводить новые color literals, если роль уже существует в token layer.
6. Не создавать generic token `accent`, который одновременно означает Lime и Purple.
7. Для новых компонентов сначала выбрать semantic role: Canvas / Surface / Workbench / Primary / Interactive / Status.
8. UI-изменения должны проходить `npm run verify` и viewport review.

## 17. Do / Don't

**Do**

- Lime filled CTA + Ink text;
- Lime chip на Navy hero;
- White active nav card на Navy;
- Dark media workspace;
- Purple focus rings;
- большие спокойные поверхности и ясные отступы.

**Don't**

- Lime text/icon на White/Canvas;
- White text на Lime;
- Purple primary button рядом с Lime primary button;
- полупрозрачная карточка вокруг каждого блока;
- multiple competing dark anchors;
- hidden/transparent sidebar text on `:active`;
- `!important` для исправления каскада.

## 18. Canonical component mapping

| Giftomat component | August v3 role |
|---|---|
| `app-shell` | Canvas |
| `topbar` | translucent White Surface |
| `tool-sidebar` | Navy Anchor |
| active nav item | White Surface + Ink + Lime icon |
| `canvas-panel` | Dark Workbench |
| `preview-stage` | Raised Dark Workbench |
| `control-panel` | White Control Surface |
| `control-heading` | Dark Hero |
| `.eyebrow` inside hero | Lime Chip + Ink |
| `primary-button` | Lime Primary |
| `download-button` | Lime Primary |
| selected segmented item | Navy Selection |
| focus-visible | Purple Interaction |
| success/error cards | semantic status colors |

August v3 считается соблюдённой только если эти роли остаются однозначными и не конкурируют между собой.
