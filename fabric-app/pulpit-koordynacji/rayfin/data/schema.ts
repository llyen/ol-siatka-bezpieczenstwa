import { ReadinessWriteback } from './ReadinessWriteback.js';
import { EscalationRequest } from './EscalationRequest.js';

export type AppSchema = {
  ReadinessWriteback: ReadinessWriteback;
  EscalationRequest: EscalationRequest;
};

export const schema = [ReadinessWriteback, EscalationRequest];
