import { defineConfig, mergeConfig } from 'vite';
import upstreamConfig from './vite.config.js';

export default defineConfig(async (environment) => {
  const resolvedUpstreamConfig = typeof upstreamConfig === 'function'
    ? await upstreamConfig(environment)
    : upstreamConfig;

  return mergeConfig(resolvedUpstreamConfig, {
    esbuild: {
      drop: ['console', 'debugger'],
    },
  });
});
