---
name: Snip
description: Native Windows capture and annotation utility.
colors:
  surface: "#171717"
  row: "#252525"
  hover: "#333333"
  text: "#F5F5F5"
  muted: "#B8B8B8"
  accent: "#E8DBBE"
  action: "#AD8326"
  action-hover: "#8A6820"
  action-text: "#FFFFFF"
  selected: "#E8E8E8"
  markup: "#404040"
  redaction: "#000000"
typography:
  title:
    fontFamily: "Segoe UI"
    fontSize: "15pt"
    fontWeight: 700
  dialog-title:
    fontFamily: "Segoe UI"
    fontSize: "13pt"
    fontWeight: 700
  input:
    fontFamily: "Segoe UI"
    fontSize: "11pt"
    fontWeight: 400
  body:
    fontFamily: "Segoe UI"
    fontSize: "10pt"
    fontWeight: 400
  selection-label:
    fontFamily: "Segoe UI"
    fontSize: "11pt"
    fontWeight: 700
rounded:
  control: "0px"
spacing:
  row-gap-half: "3px"
  tool-gap: "6px"
  compact: "8px"
  editor-inset: "10px"
  control-inline: "12px"
  dialog-inset: "16px"
components:
  button:
    backgroundColor: "{colors.row}"
    textColor: "{colors.text}"
    typography: "{typography.body}"
    rounded: "{rounded.control}"
    padding: "7px 12px"
  button-primary:
    backgroundColor: "{colors.action}"
    textColor: "{colors.action-text}"
    typography: "{typography.body}"
    rounded: "{rounded.control}"
    padding: "7px 12px"
  button-primary-hover:
    backgroundColor: "{colors.action-hover}"
    textColor: "{colors.action-text}"
  button-active:
    backgroundColor: "{colors.hover}"
    textColor: "{colors.text}"
  input:
    backgroundColor: "{colors.row}"
    textColor: "{colors.text}"
    typography: "{typography.input}"
    rounded: "{rounded.control}"
  tool-selected:
    backgroundColor: "{colors.selected}"
    textColor: "{colors.surface}"
---

# Design System: Snip

## Overview

**Creative North Star: "Native Windows, task first"**

Dark neutral surfaces, white text and SRC gold actions share the approved theme with Silent Type and Dictate. Segoe UI, labeled controls and visible focus carry the interface. This is a Windows Tkinter app; native window chrome and scrollbars remain platform controls.

**Key Characteristics:**
- Compact, rectangular controls.
- Gold identifies primary actions; light gold marks focus and selection outlines.
- Selected tools use gray. Charcoal marks annotations; captured images retain their own colors.

## Colors

### Primary

Gold action fills Capture and Save, with white labels and darker-gold hover. Light-gold accent supplies dark-surface focus, primary-button edges, region outlines and dimensions. Selected tools use light gray with dark text. URL errors use ordinary text and explanatory wording.

White labels on solid gold retain the approved brand exception. This pairing does not establish ordinary small-text contrast compliance.

### Annotation

`markup` is charcoal for arrows, boxes and drawing previews. `redaction` is opaque black applied to image pixels.

### Neutral

`surface` is the window and canvas background. `row` separates controls from that surface. `hover` is the Tk button active background, with `text` as active foreground. `text` carries main copy; `muted` carries shortcut guidance and URL instructions.

The frontmatter records the colors used by these documented surfaces. Other constants in `theme.py` are not permission to introduce new states or decoration.

## Typography

Segoe UI is the only application font in these surfaces. Tk positive font sizes are points; padding and geometry are pixels. Windows/Tk scaling affects their rendered size. No custom line-height, letter-spacing or fallback stack is defined.

- `title`: palette name.
- `dialog-title`: URL field heading.
- `input`: editable URL.
- `body`: buttons, instructions, validation and annotation guidance.
- `selection-label`: live region dimensions.

## Layout

The palette appears near the pointer within its monitor's work area, including monitors with negative origins. It has 16px horizontal insets and vertically stacked, full-width actions with 3px padding above and below each row. Width is the greater of 350px or the rows' requested width plus 48px, capped at work-area width minus 16px. Position preserves an 8px work-area margin. Height is capped at work-area height minus 16px; overflow gains a vertical scrollbar. Keyboard focus scrolls its action into view.

The URL prompt has 16px outer padding, width capped at 560px or work-area width minus 32px, and initial height 240px. The field fills the available width with 7px internal vertical padding. Cancel and Capture align right with an 8px gap. Validation has reserved space below the field.

The editor places tools in one row, then guidance and Save in a separate row, followed by the image canvas. Tool-row insets are 10px horizontally and 8px vertically; tools have 6px gaps and Undo has a 12px leading gap. The second row has 12px horizontal insets. Guidance wraps to the row width minus the Save button and 16px, with a 120px minimum wrap length. The canvas has 10px side/bottom insets and both scrollbars.

Editor display scale is the minimum of 1, `(work-area width - 80) / image width`, and `(work-area height * 4) / image height`. Small images are not enlarged. Initial width is capped at work-area width minus 40px and otherwise at least 680px. Minimum width is capped at work-area width minus 40px and otherwise the greater of 480px or toolbar requested width plus 20px. Minimum height is the lesser of 300px and work-area height minus 40px. Narrow windows scroll the image horizontally; drawing coordinates include both scroll offsets.

The region overlay covers the captured desktop image at its physical origin. Its contents are the capture, not a responsive document. There are no CSS breakpoints or website text-column conventions in this native layout.

## Elevation & Depth

Application surfaces have no custom shadows, gradients or animated transitions. Tonal contrast separates controls. Windows supplies framed-dialog chrome; the capture palette and region overlay are borderless and topmost. The region overlay reduces the captured image to 35% brightness and reveals the undimmed selection while dragging.

## Shapes

Application-drawn controls and selections are rectangular. Buttons have flat relief, zero border width and a 2px focus highlight; selected annotation tools use sunken relief. Native window corners and scrollbars are controlled by Windows/Tk, not by a project radius token.

## Components

### Buttons

Secondary actions use `button`; Capture and Save use `button-primary`. Secondary active state uses `button-active`; primary active state uses `button-primary-hover`. All shared buttons accept keyboard focus, use a hand cursor and show an accent focus highlight against the surrounding surface. Their 12px/7px padding supplements Tk's text and highlight geometry; it is not a fixed target size.

### Capture palette

Action rows show a letter shortcut and a text label. The first action receives focus. Up/Down wrap through actions; Return invokes the focused button. Letter shortcuts accept lower/uppercase keys. Escape or focus leaving the palette closes it. A wheel scrolls overflowing actions. Preserve focus-driven scrolling when adding actions.

### URL field and validation

The field uses flat relief, a 2px focus highlight and a text-colored insertion cursor. It starts focused. Return in the entry or on Capture submits; Return on Cancel cancels. Escape cancels. Invalid input leaves the dialog open and displays: “Enter a valid web address without embedded login details.” The dialog grabs input while open. It does not automatically read or replace the clipboard.

### Annotation tools and image canvas

Arrow, Box, Blur and Redact are labeled buttons. Arrow starts selected; selection changes fill and relief. Undo remains a separate action. Save is labeled “Save + copy” or “Save PNG” according to configuration. Guidance states: “Redact covers pixels. Blur only softens them.”

Arrows and boxes use the markup color; saved stroke width is the greater of 4px or image width divided by 400, rounded down. Arrow preview width is 3px; rectangular preview width is 2px. Blur previews have a 5px/3px dash. Blur applies a 14px Gaussian radius; Redact fills pixels black. Image edits preserve the original and save a separate PNG.

The wheel scrolls vertically. Ctrl+Z undoes, Ctrl+S saves, and Escape closes. Closing with unsaved operations asks whether to discard them. A save failure retains the open edits. Both native scrollbars remain available at narrow sizes.

### Region selection

A crosshair and pointer drag define the selection. The outline is 2px accent with a bold dimensions label. The label appears above the selection when space permits, otherwise below. Escape or right-click cancels. Selections under 4px in either dimension cancel. The screenshot is taken before the overlay appears.

These are implemented focus, keyboard and error conventions, not a claim of screen-reader support or accessibility conformance. Region selection and annotation drawing require pointer input in the current implementation.

## Do's and Don'ts

### Do:
- **Do** retain gold actions, gray selected tools and charcoal annotation strokes.
- **Do** reuse the shared theme and button styles.
- **Do** preserve labeled actions, visible focus and keyboard cancellation.
- **Do** keep the image accessible through both scrollbars when the editor is narrowed.
- **Do** retain the captured image's colors and distinguish Blur from Redact in text.

### Don't:
- **Don't** add decorative fonts, gradients or bespoke window chrome.
- **Don't** let a dialog-wide Return handler override the focused Cancel button.
- **Don't** describe native Tk behavior as HTML/CSS or claim untested accessibility compliance.
