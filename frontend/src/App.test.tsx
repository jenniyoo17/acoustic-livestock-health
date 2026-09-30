import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import App from './App';

describe('App', () => {
  it('shows the project name, running state, and medical disclaimer', () => {
    const markup = renderToStaticMarkup(createElement(App));

    expect(markup).toContain('Acoustic Livestock Health');
    expect(markup).toContain('Early-Warning System');
    expect(markup).toContain('Frontend is running');
    expect(markup).toContain('Acoustic early-warning anomaly detection only.');
    expect(markup).toContain('Veterinary verification required.');
  });
});
