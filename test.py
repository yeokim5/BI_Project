from datamodel import OrderDepth, TradingState, Order
from typing import Tuple, List, Dict

class Trader:
    def __init__(self):
        # ── Constants ────────────────────────────────────────────────────────
        self.LIMIT = 80
        
        # ── State Tracking ───────────────────────────────────────────────────
        # EMAs react faster to sudden market shifts than simple moving averages
        self.emas = {"ASH_COATED_OSMIUM": None, "INTARIAN_PEPPER_ROOT": None}
        
        # Alpha controls how fast the EMA updates (higher = faster reaction)
        # 0.15 gives a good balance of smoothing noise but tracking the true price
        self.alpha = 0.15 

    def bid(self):
        # A conservative bid to secure top 50% without bleeding PnL.
        return 950

    def run(self, state: TradingState) -> Tuple[Dict[str, List[Order]], int, str]:
        result = {}
        
        for product in ["ASH_COATED_OSMIUM", "INTARIAN_PEPPER_ROOT"]:
            if product in state.order_depths:
                od = state.order_depths[product]
                best_ask = min(od.sell_orders.keys()) if od.sell_orders else None
                best_bid = max(od.buy_orders.keys()) if od.buy_orders else None
                
                if best_ask is None or best_bid is None:
                    continue
                    
                mid_price = (best_ask + best_bid) / 2.0
                
                # 1. Update Dynamic Fair Value
                if self.emas[product] is None:
                    self.emas[product] = mid_price
                else:
                    self.emas[product] = self.alpha * mid_price + (1 - self.alpha) * self.emas[product]
                    
                fv = self.emas[product]
                position = state.position.get(product, 0)
                
                # 2. Calculate Inventory Skew
                # If we are long (position > 0), skew is positive.
                # Subtracting this skew forces our bids and asks DOWN, helping us exit the position.
                # Max skew is roughly 4 ticks when at max position.
                skew = (position / self.LIMIT) * 4.0 
                
                # 3. Dynamic Margins
                spread = best_ask - best_bid
                margin = max(1.0, spread * 0.4) 
                
                # Desired prices based on Fair Value, margin, and our inventory risk
                target_bid = int(fv - margin - skew)
                target_ask = int(fv + margin - skew)
                
                # Pennying safety checks: never quote worse than the current best spread edges
                target_bid = min(target_bid, best_ask - 1)
                target_ask = max(target_ask, best_bid + 1)
                
                orders = []
                current_pos = position
                
                # 4. Take Liquidity (Clear Arbitrage against Skewed FV)
                # If the market gives us a price better than our risk-adjusted FV, take it immediately
                for ask_price, vol in sorted(od.sell_orders.items()):
                    if ask_price < fv - skew and current_pos < self.LIMIT:
                        buy_qty = min(self.LIMIT - current_pos, -vol)
                        if buy_qty > 0:
                            orders.append(Order(product, ask_price, buy_qty))
                            current_pos += buy_qty
                            
                for bid_price, vol in sorted(od.buy_orders.items(), reverse=True):
                    if bid_price > fv - skew and current_pos > -self.LIMIT:
                        sell_qty = min(self.LIMIT + current_pos, vol)
                        if sell_qty > 0:
                            orders.append(Order(product, bid_price, -sell_qty))
                            current_pos -= sell_qty
                
                # 5. Make Liquidity (Passive Market Making)
                buy_room = self.LIMIT - current_pos
                if buy_room > 0:
                    orders.append(Order(product, target_bid, buy_room))
                    
                sell_room = -self.LIMIT - current_pos
                if sell_room < 0:
                    orders.append(Order(product, target_ask, sell_room))
                    
                result[product] = orders

        return result, 0, ""