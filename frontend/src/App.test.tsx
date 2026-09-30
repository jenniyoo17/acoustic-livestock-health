import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import App from './App';

describe('App Component Skeleton', () => {
  it('renders system title correctly', () => {
    render(<App />);
    expect(screen.getByText(/SIH 2026: Acoustic Livestock Health System/i)).toBeInTheDocument();
  });
});
