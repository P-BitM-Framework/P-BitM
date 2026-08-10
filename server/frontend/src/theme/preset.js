import { definePreset } from '@primeuix/themes'
import Material from '@primeuix/themes/material'

const brandOrange = {
  50: '#fff4ef',
  100: '#ffe2d5',
  200: '#ffc5ad',
  300: '#fda586',
  400: '#fd926b',
  500: '#ee492a',
  600: '#d83b21',
  700: '#b92f19',
  800: '#942a1b',
  900: '#77261c',
  950: '#401008'
}

const softStatusColorScheme = {
  light: {
    primary: { background: 'color-mix(in srgb, {primary.500}, transparent 88%)', color: '{primary.700}' },
    secondary: { background: 'color-mix(in srgb, {surface.500}, transparent 90%)', color: '{surface.600}' },
    success: { background: 'color-mix(in srgb, {green.500}, transparent 88%)', color: '{green.700}' },
    info: { background: 'color-mix(in srgb, {sky.500}, transparent 88%)', color: '{sky.700}' },
    warn: { background: 'color-mix(in srgb, {orange.500}, transparent 88%)', color: '{orange.700}' },
    danger: { background: 'color-mix(in srgb, {red.500}, transparent 88%)', color: '{red.700}' },
    contrast: { background: 'color-mix(in srgb, {surface.950}, transparent 90%)', color: '{surface.900}' }
  },
  dark: {
    primary: { background: 'color-mix(in srgb, {primary.500}, transparent 84%)', color: '{primary.300}' },
    secondary: { background: 'color-mix(in srgb, {surface.400}, transparent 88%)', color: '{surface.300}' },
    success: { background: 'color-mix(in srgb, {green.500}, transparent 84%)', color: '{green.300}' },
    info: { background: 'color-mix(in srgb, {sky.500}, transparent 84%)', color: '{sky.300}' },
    warn: { background: 'color-mix(in srgb, {orange.500}, transparent 84%)', color: '{orange.300}' },
    danger: { background: 'color-mix(in srgb, {red.500}, transparent 84%)', color: '{red.300}' },
    contrast: { background: 'color-mix(in srgb, {surface.0}, transparent 88%)', color: '{surface.100}' }
  }
}

export const BitmPreset = definePreset(Material, {
  primitive: {
    orange: brandOrange
  },
  semantic: {
    transitionDuration: '0.16s',
    primary: Object.fromEntries(
      Object.keys(brandOrange).map((shade) => [shade, `{orange.${shade}}`])
    ),
    focusRing: {
      width: '1px',
      style: 'solid',
      color: '{primary.color}',
      offset: '2px',
      shadow: 'none'
    },
    formField: {
      paddingX: '0.75rem',
      paddingY: '0.5rem',
      borderRadius: '8px',
      focusRing: {
        width: '0',
        style: 'none',
        color: 'transparent',
        offset: '0',
        shadow: 'none'
      }
    },
    content: {
      borderRadius: '10px'
    },
    overlay: {
      select: { borderRadius: '10px' },
      popover: { borderRadius: '10px' },
      modal: { borderRadius: '14px' }
    },
    colorScheme: {
      light: {
        surface: {
          0: '#ffffff',
          50: '#f7f7f8',
          100: '#f1f1f3',
          200: '#e4e4e7',
          300: '#d4d4d8',
          400: '#a1a1aa',
          500: '#71717a',
          600: '#52525b',
          700: '#3f3f46',
          800: '#27272a',
          900: '#18181b',
          950: '#09090b'
        },
        primary: {
          color: '{primary.500}',
          contrastColor: '#ffffff',
          hoverColor: '{primary.600}',
          activeColor: '{primary.700}'
        },
        highlight: {
          background: 'color-mix(in srgb, {primary.500}, transparent 90%)',
          focusBackground: 'color-mix(in srgb, {primary.500}, transparent 84%)',
          color: '{primary.700}',
          focusColor: '{primary.800}'
        },
        formField: {
          background: '#f7f7f8',
          disabledBackground: '#f1f1f3',
          filledBackground: '#f7f7f8',
          filledHoverBackground: '#f1f1f3',
          filledFocusBackground: '#f7f7f8',
          borderColor: '#d4d4d8',
          hoverBorderColor: '#a1a1aa',
          focusBorderColor: '{primary.500}',
          color: '#18181b',
          disabledColor: '#a1a1aa',
          placeholderColor: '#71717a',
          iconColor: '#71717a'
        },
        text: {
          color: '#18181b',
          hoverColor: '#09090b',
          mutedColor: '#52525b',
          hoverMutedColor: '#3f3f46'
        },
        content: {
          background: '#ffffff',
          hoverBackground: '#e6e6ea',
          borderColor: '#d4d4d8',
          color: '#18181b',
          hoverColor: '#09090b'
        }
      },
      dark: {
        surface: {
          0: '#fafafa',
          50: '#f4f4f5',
          100: '#e4e4e7',
          200: '#d4d4d8',
          300: '#a1a1aa',
          400: '#8b8b95',
          500: '#71717a',
          600: '#52525b',
          700: '#3f3f46',
          800: '#27272a',
          900: '#18181b',
          950: '#0c0c0f'
        },
        primary: {
          color: '{primary.500}',
          contrastColor: '#ffffff',
          hoverColor: '{primary.400}',
          activeColor: '{primary.600}'
        },
        highlight: {
          background: 'color-mix(in srgb, {primary.500}, transparent 84%)',
          focusBackground: 'color-mix(in srgb, {primary.500}, transparent 76%)',
          color: '#f4f4f5',
          focusColor: '#ffffff'
        },
        formField: {
          background: '#1c1c20',
          disabledBackground: '#242429',
          filledBackground: '#1c1c20',
          filledHoverBackground: '#242429',
          filledFocusBackground: '#1c1c20',
          borderColor: '#34343b',
          hoverBorderColor: '#494952',
          focusBorderColor: '{primary.500}',
          color: '#f4f4f5',
          disabledColor: '#71717a',
          placeholderColor: '#92929d',
          iconColor: '#92929d'
        },
        text: {
          color: '#f4f4f5',
          hoverColor: '#ffffff',
          mutedColor: '#92929d',
          hoverMutedColor: '#c4c4cc'
        },
        content: {
          background: '#151518',
          hoverBackground: '#2d2d34',
          borderColor: '#34343b',
          color: '#f4f4f5',
          hoverColor: '#ffffff'
        },
        overlay: {
          select: {
            background: '#151518',
            borderColor: '#34343b',
            color: '#f4f4f5'
          },
          popover: {
            background: '#151518',
            borderColor: '#34343b',
            color: '#f4f4f5'
          },
          modal: {
            background: '#151518',
            borderColor: '#34343b',
            color: '#f4f4f5'
          }
        }
      }
    }
  },
  components: {
    tag: {
      colorScheme: softStatusColorScheme
    },
    badge: {
      colorScheme: softStatusColorScheme
    },
    chip: {
      root: {
        paddingX: '0.7rem',
        paddingY: '0.45rem'
      },
      colorScheme: {
        light: {
          root: {
            background: 'color-mix(in srgb, {surface.500}, transparent 90%)',
            color: '{surface.700}'
          },
          icon: { color: '{surface.600}' },
          removeIcon: { color: '{surface.600}' }
        },
        dark: {
          root: {
            background: 'color-mix(in srgb, {surface.400}, transparent 86%)',
            color: '{surface.200}'
          },
          icon: { color: '{surface.300}' },
          removeIcon: { color: '{surface.300}' }
        }
      }
    }
  }
})
