/**
 * Sample JavaScript file with code quality issues
 * Used for testing code analyzer
 */

// TODO: Refactor this entire file
// FIXME: Security vulnerabilities present

// Hardcoded secrets - security issue
const API_KEY = 'pk_live_1234567890abcdef';
const SECRET = 'my_secret_key_123';

/**
 * Function with too many parameters
 * Should be flagged for refactoring
 */
function createUser(firstName, lastName, email, phone, address, city) {
    return {
        firstName,
        lastName,
        email,
        phone,
        address,
        city
    };
}

/**
 * Very long and complex function
 * Over 50 lines with high complexity
 */
function processOrderData(orders) {
    const results = [];
    
    // HACK: This is a temporary solution
    for (let i = 0; i < orders.length; i++) {
        const order = orders[i];
        
        if (order.status === 'pending') {
            if (order.total > 100) {
                if (order.customer.isPremium) {
                    if (order.items.length > 5) {
                        results.push({
                            ...order,
                            discount: 0.25,
                            priority: 'high'
                        });
                    } else {
                        results.push({
                            ...order,
                            discount: 0.15,
                            priority: 'medium'
                        });
                    }
                } else {
                    if (order.items.length > 5) {
                        results.push({
                            ...order,
                            discount: 0.10,
                            priority: 'medium'
                        });
                    } else {
                        results.push({
                            ...order,
                            discount: 0.05,
                            priority: 'low'
                        });
                    }
                }
            } else {
                results.push({
                    ...order,
                    discount: 0,
                    priority: 'low'
                });
            }
        } else if (order.status === 'processing') {
            if (order.total > 200) {
                results.push({
                    ...order,
                    priority: 'high'
                });
            } else {
                results.push({
                    ...order,
                    priority: 'medium'
                });
            }
        } else if (order.status === 'completed') {
            results.push({
                ...order,
                priority: 'archive'
            });
        }
    }
    
    return results;
}

/**
 * Function with security vulnerability
 */
function executeCode(code) {
    // Security issue: eval
    return eval(code);
}

/**
 * Another function with too many parameters
 */
function calculateShipping(weight, distance, speed, insurance, packaging, handling, customs) {
    let cost = weight * 0.5;
    cost += distance * 0.1;
    
    if (speed === 'express') {
        cost *= 2;
    }
    
    if (insurance) {
        cost += 10;
    }
    
    if (packaging === 'premium') {
        cost += 5;
    }
    
    cost += handling;
    cost += customs;
    
    return cost;
}

// XXX: Remove this before production
function debugFunction() {
    console.log('Debug info');
}

class DataManager {
    constructor() {
        this.data = [];
    }
    
    /**
     * Complex method that needs refactoring
     */
    processData(items) {
        const processed = [];
        
        for (let item of items) {
            if (item.type === 'A') {
                if (item.value > 50) {
                    processed.push(item.value * 2);
                } else {
                    processed.push(item.value);
                }
            } else if (item.type === 'B') {
                if (item.value < 100) {
                    processed.push(item.value / 2);
                } else {
                    processed.push(item.value);
                }
            } else {
                processed.push(0);
            }
        }
        
        return processed;
    }
}

module.exports = {
    createUser,
    processOrderData,
    calculateShipping,
    DataManager
};