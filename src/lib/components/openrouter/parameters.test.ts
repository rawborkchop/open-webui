import { describe, expect, it } from 'vitest';
import { updateParameter, readParameter, resetProviderOverrides } from './parameters';
describe('OpenRouter parameter controls', () => {
	it('updates a nested parameter without discarding its siblings or mutating the original', () => {
		// Arrange
		const original = { custom_params: { reasoning: { effort: 'low', exclude: false } } };
		// Act
		const result = updateParameter(original, 'reasoning.effort', 'high', { access: 'editable', type: 'string' });
		// Assert
		expect(result.custom_params.reasoning).toEqual({ effort: 'high', exclude: false });
		expect(original.custom_params.reasoning.effort).toBe('low');
	});
	it('removes a value so the provider default can apply', () => {
		// Arrange
		const original = { temperature: 0.5, custom_params: { temperature: 0.5 } };
		// Act
		const result = updateParameter(original, 'temperature', '', { access: 'editable', type: 'number' });
		// Assert
		expect(result.temperature).toBeUndefined();
		expect(result.custom_params.temperature).toBeUndefined();
	});
	it('reads JSON stored by the existing custom parameter editor', () => {
		// Arrange
		const original = { custom_params: { reasoning: '{"effort":"high"}' } };
		// Act
		const result = readParameter(original, 'reasoning.effort');
		// Assert
		expect(result).toBe('high');
	});
	it('clears provider overrides while preserving application controls', () => {
		// Arrange
		const original = { temperature: 2, custom_params: { forbidden: true }, tool_approval_mode: 'ask', model_controls: {} };
		// Act
		const result = resetProviderOverrides(original);
		// Assert
		expect(result).toEqual({ tool_approval_mode: 'ask', model_controls: {}, custom_params: {} });
	});
});
