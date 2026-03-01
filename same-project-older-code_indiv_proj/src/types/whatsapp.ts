// Minimal WhatsApp types used by the project

export interface WhatsappTextMessage {
	from: string;
	body: string;
}

export interface WhatsappWebhookPayload {
	object: string;
	entry: Array<any>;
}

export type WhatsappPayload = WhatsappWebhookPayload;