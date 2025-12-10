---
name: ui-development
description: Frontend development, React/Vue/Svelte components, CSS/Tailwind styling, accessibility, and responsive design. Use when building user interfaces, components, or working on frontend code.
---

# UI Development Skill

## When to Use
- Building React/Vue/Svelte components
- Styling with CSS/Tailwind/styled-components
- Implementing responsive designs
- Fixing accessibility issues
- Optimizing frontend performance

## Component Design Principles

### React Patterns
```tsx
// Prefer functional components with hooks
// Use TypeScript for type safety
// Keep components small and focused
// Lift state only when necessary
// Use composition over inheritance

interface Props {
  title: string;
  onAction: () => void;
  children?: React.ReactNode;
}

export function Component({ title, onAction, children }: Props) {
  const [state, setState] = useState<State>(initialState);

  // Memoize expensive computations
  const computed = useMemo(() => expensiveCalc(state), [state]);

  // Memoize callbacks passed to children
  const handleClick = useCallback(() => {
    onAction();
  }, [onAction]);

  return (/* JSX */);
}
```

### State Management Hierarchy
1. **Local state** - useState for component-specific
2. **Lifted state** - Props for parent-child sharing
3. **Context** - For prop drilling avoidance
4. **External store** - Zustand/Redux for complex global state
5. **Server state** - React Query/SWR for API data

## Accessibility (a11y) Checklist
- [ ] Semantic HTML (nav, main, article, button vs div)
- [ ] ARIA labels where needed
- [ ] Keyboard navigation works
- [ ] Focus management for modals/dialogs
- [ ] Color contrast >= 4.5:1
- [ ] Alt text for images
- [ ] Form labels linked to inputs
- [ ] Error messages announced to screen readers

## Performance Optimization
1. **Code splitting** - Dynamic imports, lazy loading
2. **Memoization** - React.memo, useMemo, useCallback
3. **Virtualization** - For long lists (react-window)
4. **Image optimization** - WebP, lazy loading, srcset
5. **Bundle analysis** - webpack-bundle-analyzer

## CSS Best Practices
```css
/* Use CSS custom properties for theming */
:root {
  --color-primary: #3b82f6;
  --spacing-md: 1rem;
}

/* Mobile-first responsive design */
.container {
  padding: var(--spacing-md);
}

@media (min-width: 768px) {
  .container {
    max-width: 768px;
  }
}
```

## Testing Strategy
- **Unit** - Individual components with React Testing Library
- **Integration** - Component interactions
- **E2E** - Critical user flows with Playwright/Cypress
- **Visual regression** - Chromatic/Percy

## Common Commands
```bash
# Dev server
npm run dev

# Type checking
npx tsc --noEmit

# Lint & format
npm run lint && npm run format

# Bundle analysis
npx vite-bundle-visualizer
```
