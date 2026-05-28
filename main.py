"""
Chess — Kivy  (Desktop + Android/Mobile)
=========================================
Fixes vs v1:
  • Pieces drawn using standard high-quality PNG images (real chess coins)
  • Fully responsive: portrait → board on top, panel below
                      landscape → board left, panel right
  • Modern dark "game app" UI
  • Touch-friendly: all tap targets ≥ 44dp

Run:  python chess_kivy.py
APK:  buildozer android debug   (needs buildozer.spec)
"""

# ── kivy config BEFORE any other kivy import ──────────────────────────────────
from kivy.config import Config
Config.set("graphics", "resizable", "1")
Config.set("input", "mouse", "mouse,multitouch_on_demand")

import math
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.graphics import (Color, Rectangle, Ellipse, Line,
                            RoundedRectangle, Triangle, Mesh, StencilPush,
                            StencilUse, StencilUnUse, StencilPop)
from kivy.core.window import Window
from kivy.metrics import dp, sp
from kivy.clock import Clock
from kivy.utils import get_color_from_hex as gch

# ═══════════════════════════════════════════════════════════════════════════════
#  COLOUR PALETTE
# ═══════════════════════════════════════════════════════════════════════════════
C = dict(
    light_sq  = gch("f0d9b5"), dark_sq   = gch("b58863"),
    sel_l     = gch("f6f669"), sel_d     = gch("baca2b"),
    last_l    = gch("cdd16a"), last_d    = gch("aaa23a"),
    check     = gch("c83c3c"),
    cap_l     = gch("e07060"), cap_d     = gch("b84040"),
    dot_l     = gch("9dab7c"), dot_d     = gch("6b7a4a"),
    bg        = gch("0f1318"),
    panel_bg  = gch("090d11"),
    card      = gch("181e26"),
    gold      = gch("c8a033"),
    gold_dim  = gch("8a6e22"),
    txt       = gch("e6edf3"),
    txt_dim   = gch("7d8590"),
    red       = gch("da3633"),
    btn_hover = gch("a07828"),
    white_pc  = gch("f5f0e8"),  # white piece fill
    white_out = gch("c8b89a"),  # white piece outline
    black_pc  = gch("1a1208"),  # black piece fill
    black_out = gch("5a4020"),  # black piece outline
)

FILES = "abcdefgh"
RANKS = "87654321"

# ═══════════════════════════════════════════════════════════════════════════════
#  CHESS LOGIC  (identical to original – no changes)
# ═══════════════════════════════════════════════════════════════════════════════
def in_bounds(r,c): return 0<=r<8 and 0<=c<8
def opp(color):     return "black" if color=="white" else "white"

class Piece:
    def __init__(self,color,kind): self.color=color; self.kind=kind; self.moved=False
    def pseudo_moves(self,r,c,board,ep=None,cr=None): return []

class Pawn(Piece):
    def __init__(self,color): super().__init__(color,"pawn")
    def pseudo_moves(self,r,c,board,ep=None,cr=None):
        moves=[]; d=-1 if self.color=="white" else 1; start=6 if self.color=="white" else 1
        if in_bounds(r+d,c) and board[r+d][c] is None:
            moves.append((r+d,c))
            if r==start and board[r+2*d][c] is None: moves.append((r+2*d,c))
        for dc in(-1,1):
            nr,nc=r+d,c+dc
            if in_bounds(nr,nc):
                t=board[nr][nc]
                if t and t.color!=self.color: moves.append((nr,nc))
                if ep and (nr,nc)==ep:        moves.append((nr,nc))
        return moves

class Rook(Piece):
    def __init__(self,color): super().__init__(color,"rook")
    def pseudo_moves(self,r,c,board,ep=None,cr=None):
        moves=[]
        for dr,dc in((-1,0),(1,0),(0,-1),(0,1)):
            nr,nc=r+dr,c+dc
            while in_bounds(nr,nc):
                t=board[nr][nc]
                if t:
                    if t.color!=self.color: moves.append((nr,nc))
                    break
                moves.append((nr,nc)); nr+=dr; nc+=dc
        return moves

class Knight(Piece):
    def __init__(self,color): super().__init__(color,"knight")
    def pseudo_moves(self,r,c,board,ep=None,cr=None):
        return [(r+dr,c+dc) for dr,dc in((-2,-1),(-2,1),(-1,-2),(-1,2),(1,-2),(1,2),(2,-1),(2,1))
                if in_bounds(r+dr,c+dc) and(board[r+dr][c+dc] is None or board[r+dr][c+dc].color!=self.color)]

class Bishop(Piece):
    def __init__(self,color): super().__init__(color,"bishop")
    def pseudo_moves(self,r,c,board,ep=None,cr=None):
        moves=[]
        for dr,dc in((-1,-1),(-1,1),(1,-1),(1,1)):
            nr,nc=r+dr,c+dc
            while in_bounds(nr,nc):
                t=board[nr][nc]
                if t:
                    if t.color!=self.color: moves.append((nr,nc))
                    break
                moves.append((nr,nc)); nr+=dr; nc+=dc
        return moves

class Queen(Piece):
    def __init__(self,color): super().__init__(color,"queen")
    def pseudo_moves(self,r,c,board,ep=None,cr=None):
        moves=[]
        for dr,dc in((-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)):
            nr,nc=r+dr,c+dc
            while in_bounds(nr,nc):
                t=board[nr][nc]
                if t:
                    if t.color!=self.color: moves.append((nr,nc))
                    break
                moves.append((nr,nc)); nr+=dr; nc+=dc
        return moves

class King(Piece):
    def __init__(self,color): super().__init__(color,"king")
    def pseudo_moves(self,r,c,board,ep=None,cr=None):
        moves=[]
        for dr,dc in((-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)):
            nr,nc=r+dr,c+dc
            if in_bounds(nr,nc) and(board[nr][nc] is None or board[nr][nc].color!=self.color):
                moves.append((nr,nc))
        if cr:
            base=7 if self.color=="white" else 0; rights=cr[self.color]
            if r==base and c==4:
                if rights["kingside"] and not board[base][5] and not board[base][6]:
                    moves.append((base,6))
                if rights["queenside"] and not board[base][3] and not board[base][2] and not board[base][1]:
                    moves.append((base,2))
        return moves

def find_king(board,color):
    for r in range(8):
        for c in range(8):
            p=board[r][c]
            if p and p.kind=="king" and p.color==color: return r,c
    return None,None

def is_attacked(board,r,c,by_color):
    no_cr={"white":{"kingside":False,"queenside":False},"black":{"kingside":False,"queenside":False}}
    for br in range(8):
        for bc in range(8):
            p=board[br][bc]
            if p and p.color==by_color and (r,c) in p.pseudo_moves(br,bc,board,None,no_cr):
                return True
    return False

def in_check(board,color):
    r,c=find_king(board,color)
    return r is not None and is_attacked(board,r,c,opp(color))

def apply_move(board,fr,fc,tr,tc,ep,promo=None):
    nb=[row[:] for row in board]; piece=nb[fr][fc]
    if piece.kind=="pawn" and ep and (tr,tc)==ep: nb[fr][tc]=None
    if piece.kind=="king":
        base=7 if piece.color=="white" else 0
        if fc==4 and tc==6: nb[base][5]=nb[base][7]; nb[base][7]=None
        elif fc==4 and tc==2: nb[base][3]=nb[base][0]; nb[base][0]=None
    if promo:
        cls={"queen":Queen,"rook":Rook,"bishop":Bishop,"knight":Knight}[promo]
        nb[tr][tc]=cls(piece.color)
    else: nb[tr][tc]=piece
    nb[fr][fc]=None; return nb

def legal_moves(board,r,c,turn,ep,cr):
    piece=board[r][c]
    if not piece or piece.color!=turn: return []
    result=[]
    for tr,tc in piece.pseudo_moves(r,c,board,ep,cr):
        if piece.kind=="king" and abs(tc-c)==2:
            base=7 if piece.color=="white" else 0
            if in_check(board,piece.color): continue
            mid=5 if tc==6 else 3
            if is_attacked(board,base,mid,opp(piece.color)): continue
            if is_attacked(board,base,tc, opp(piece.color)): continue
        nb=apply_move(board,r,c,tr,tc,ep)
        if not in_check(nb,piece.color): result.append((tr,tc))
    return result

def has_moves(board,color,ep,cr):
    for r in range(8):
        for c in range(8):
            p=board[r][c]
            if p and p.color==color and legal_moves(board,r,c,color,ep,cr): return True
    return False

def notation(rec):
    if rec.get("castle")=="K": return "O-O"
    if rec.get("castle")=="Q": return "O-O-O"
    p=rec["piece"]; L={"pawn":"","rook":"R","knight":"N","bishop":"B","queen":"Q","king":"K"}
    s=""
    if p.kind=="pawn":
        if rec.get("cap") or rec.get("ep"): s=FILES[rec["fc"]]+"x"
    else:
        s=L[p.kind]
        if rec.get("cap"): s+="x"
    s+=FILES[rec["tc"]]+RANKS[rec["tr"]]
    if rec.get("promo"): s+="="+L[rec["promo"]].upper()
    return s

class GameState:
    BACK=[Rook,Knight,Bishop,Queen,King,Bishop,Knight,Rook]
    def __init__(self): self.reset()
    def reset(self):
        self.board=[[None]*8 for _ in range(8)]; self.turn="white"
        self.ep=None
        self.cr={"white":{"kingside":True,"queenside":True},"black":{"kingside":True,"queenside":True}}
        self.history=[]; self.redo_stack=[]; self.captured={"white":[],"black":[]}; self.status="playing"
        for c,Cls in enumerate(self.BACK):
            self.board[0][c]=Cls("black"); self.board[7][c]=Cls("white")
        for c in range(8):
            self.board[1][c]=Pawn("black"); self.board[6][c]=Pawn("white")
    def get_legal(self,r,c): return legal_moves(self.board,r,c,self.turn,self.ep,self.cr)
    def needs_promo(self,fr,fc,tr):
        p=self.board[fr][fc]
        return p and p.kind=="pawn" and((p.color=="white" and tr==0)or(p.color=="black" and tr==7))
    def move(self,fr,fc,tr,tc,promo=None):
        piece=self.board[fr][fc]; opponent=opp(piece.color)
        dcap=self.board[tr][tc]
        is_ep=piece.kind=="pawn" and self.ep and(tr,tc)==self.ep
        cap=dcap or(self.board[fr][tc] if is_ep else None)
        if cap: self.captured[piece.color].append(cap)
        castle=None
        if piece.kind=="king" and fc==4:
            if tc==6: castle="K"
            elif tc==2: castle="Q"
        if piece.kind=="king":
            self.cr[piece.color]["kingside"]=False; self.cr[piece.color]["queenside"]=False
        if piece.kind=="rook":
            if fc==0: self.cr[piece.color]["queenside"]=False
            if fc==7: self.cr[piece.color]["kingside"]=False
        if dcap and dcap.kind=="rook":
            if tc==0: self.cr[dcap.color]["queenside"]=False
            if tc==7: self.cr[dcap.color]["kingside"]=False
        self.ep=((fr+tr)//2,fc) if piece.kind=="pawn" and abs(tr-fr)==2 else None
        self.board=apply_move(self.board,fr,fc,tr,tc,self.ep if is_ep else None,promo)
        rec={"piece":piece,"fr":fr,"fc":fc,"tr":tr,"tc":tc,"cap":cap,"promo":promo,"castle":castle,"ep":is_ep}
        rec["note"]=notation(rec); self.history.append(rec)
        self.turn=opponent
        chk=in_check(self.board,opponent); anyl=has_moves(self.board,opponent,self.ep,self.cr)
        if not anyl: self.status="checkmate" if chk else "stalemate"
        elif chk:    self.status="check"
        else:        self.status="playing"
    def move_pairs(self):
        pairs=[]
        for i in range(0,len(self.history),2):
            w=self.history[i]["note"]; b=self.history[i+1]["note"] if i+1<len(self.history) else ""
            pairs.append((i//2+1,w,b))
        return pairs
    def undo(self):
        if not self.history: return
        last=self.history[-1]
        moves=[(m["fr"],m["fc"],m["tr"],m["tc"],m["promo"]) for m in self.history[:-1]]
        rs=self.redo_stack+[last]; self.reset()
        for args in moves: self.move(*args)
        self.redo_stack=rs
    def redo(self):
        if not self.redo_stack: return
        m=self.redo_stack.pop(); self.move(m["fr"],m["fc"],m["tr"],m["tc"],m["promo"])


# ═══════════════════════════════════════════════════════════════════════════════
#  PIECE DRAWING  — pure canvas, no font dependency
# ═══════════════════════════════════════════════════════════════════════════════

def _draw_piece(canvas, kind, color, cx, cy, sq):
    """Draw a chess piece centred at (cx,cy) inside a square of size sq."""
    s   = sq * 0.9          # overall scale
    h   = s * 0.5

    kind_map = {
        "pawn": "p", "knight": "n", "bishop": "b", 
        "rook": "r", "queen": "q", "king": "k"
    }
    prefix = "w" if color == "white" else "b"
    source = f"assets/{prefix}{kind_map[kind]}.png"

    with canvas:
        Color(1, 1, 1, 1)  # Reset to natural image color
        Rectangle(pos=(cx - h, cy - h), size=(s, s), source=source)


# ═══════════════════════════════════════════════════════════════════════════════
#  BOARD WIDGET
# ═══════════════════════════════════════════════════════════════════════════════

class BoardWidget(Widget):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.bind(size=self._redraw, pos=self._redraw)

    def _sq(self):
        return min(self.width, self.height) / 8

    def _sq_xy(self, r, c):
        """Bottom-left corner of square (row r, col c) in Kivy coords."""
        sq = self._sq()
        bx = self.x + (self.width  - sq*8) / 2
        by = self.y + (self.height - sq*8) / 2
        return bx + c*sq, by + (7-r)*sq

    def _redraw(self, *_):
        self.canvas.clear()
        app = self.app
        g   = app.game
        sq  = self._sq()
        sel = app.sel
        valid = set(app.valid)
        last = g.history[-1] if g.history else None

        kchk = None
        if g.status in ("check","checkmate"):
            kr,kc = find_king(g.board, g.turn)
            kchk = (kr, kc)

        cap_sq  = {(r,c) for r,c in valid if g.board[r][c]}
        move_sq = {(r,c) for r,c in valid if not g.board[r][c]}

        with self.canvas:
            # ── 1. Square fills ───────────────────────────────────────────────
            for r in range(8):
                for c in range(8):
                    x,y = self._sq_xy(r,c)
                    lt  = (r+c)%2==0
                    if kchk and (r,c)==kchk:
                        Color(*C["check"])
                    elif sel==(r,c):
                        Color(*(C["sel_l"] if lt else C["sel_d"]))
                    elif (r,c) in cap_sq:
                        Color(*(C["cap_l"] if lt else C["cap_d"]))
                    elif last and (r,c) in ((last["fr"],last["fc"]),(last["tr"],last["tc"])):
                        Color(*(C["last_l"] if lt else C["last_d"]))
                    elif lt:
                        Color(*C["light_sq"])
                    else:
                        Color(*C["dark_sq"])
                    Rectangle(pos=(x,y), size=(sq,sq))

            # ── 2. Board border ───────────────────────────────────────────────
            bx,by = self._sq_xy(0,0); bx2 = bx; by2 = by-sq*7  # top-left of board
            # thin gold border
            bx0,by0 = self._sq_xy(7,0)
            Color(*C["gold"], 0.4)
            Line(rectangle=(bx0, by0, sq*8, sq*8), width=dp(1.5))

            # ── 3. Dots on empty move squares ─────────────────────────────────
            for (mr,mc) in move_sq:
                x,y = self._sq_xy(mr,mc)
                cx2 = x+sq/2; cy2 = y+sq/2; r2 = sq*0.15
                lt = (mr+mc)%2==0
                Color(*(C["dot_l"] if lt else C["dot_d"]), 0.9)
                Ellipse(pos=(cx2-r2, cy2-r2), size=(r2*2, r2*2))

            # ── 4. Move arrows ─────────────────────────────────────────────────
            if sel and valid:
                sx,sy = self._sq_xy(sel[0],sel[1]); sx+=sq/2; sy+=sq/2
                for (mr,mc) in valid:
                    dx,dy = self._sq_xy(mr,mc); dx+=sq/2; dy+=sq/2
                    Color(*C["gold"], 0.45)
                    Line(points=[sx,sy,dx,dy], width=dp(1.5), cap="round")

            # ── 5. Coordinate labels (tiny, corner-anchored) ──────────────────
            # rendered via Label children; skip in canvas pass

            # ── 6. Pieces ─────────────────────────────────────────────────────
            # Ghost pieces (valid-move destinations, selected piece half-transparent)
            sel_piece = g.board[sel[0]][sel[1]] if sel else None
            if sel_piece:
                for (mr,mc) in move_sq:
                    gx,gy = self._sq_xy(mr,mc)
                    gcx = gx+sq/2; gcy = gy+sq/2
                    # blue-tint ghost: draw with low alpha
                    Color(0.4,0.65,0.9, 0.35)
                    Ellipse(pos=(gcx-sq*0.35, gcy-sq*0.35), size=(sq*0.7,sq*0.7))

            # Real pieces
            for r in range(8):
                for c in range(8):
                    p = g.board[r][c]
                    if not p: continue
                    x,y = self._sq_xy(r,c)
                    _draw_piece(self.canvas, p.kind, p.color, x+sq/2, y+sq/2, sq)

            # ── 7. Coordinate text ────────────────────────────────────────────
            fsz = max(9, int(sq*0.16))
            Color(*C["gold"], 0.9)
            for i in range(8):
                # file letters bottom
                x,y = self._sq_xy(7,i)
                # rank numbers left
                xr,yr = self._sq_xy(i,0)

        # coordinate labels as child Label widgets
        self._add_coords(sq)

    def _add_coords(self, sq):
        for child in list(self.children):
            self.remove_widget(child)
        fsz = max(sp(7), sq * 0.14)
        for i in range(8):
            # file letter bottom-right of bottom row
            x,y = self._sq_xy(7,i)
            fl = Label(text=FILES[i], font_size=fsz, bold=True,
                       color=C["gold"], pos=(x+sq-fsz*1.3,y), size=(fsz*1.3,fsz*1.3))
            self.add_widget(fl)
            # rank number top-left of each rank
            xr,yr = self._sq_xy(i,0)
            rl = Label(text=RANKS[i], font_size=fsz, bold=True,
                       color=C["gold"], pos=(xr,yr+sq-fsz*1.3), size=(fsz*1.3,fsz*1.3))
            self.add_widget(rl)

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos): return False
        sq = self._sq()
        bx,_ = self._sq_xy(0,0)
        _,by0 = self._sq_xy(7,0)
        c = int((touch.x - bx) / sq)
        r = int((touch.y - by0) / sq)
        r = 7 - r   # flip: row 0 is top
        if not in_bounds(r,c): return True
        self.app.handle_click(r,c)
        return True


# ═══════════════════════════════════════════════════════════════════════════════
#  STYLED BUTTON
# ═══════════════════════════════════════════════════════════════════════════════

def make_btn(text, callback, bg=None, fg=None):
    bg = bg or C["gold"]
    fg = fg or C["panel_bg"]
    b = Button(
        text=text,
        size_hint=(1, None), height=dp(44),
        background_normal="", background_color=(*bg[:3],1),
        color=(*fg[:3],1),
        font_size=sp(13), bold=True,
    )
    b.bind(on_release=lambda *_: callback())
    return b


# ═══════════════════════════════════════════════════════════════════════════════
#  SIDE PANEL
# ═══════════════════════════════════════════════════════════════════════════════

class SidePanel(BoxLayout):
    def __init__(self, app, **kwargs):
        kwargs.setdefault("orientation","vertical")
        kwargs.setdefault("spacing", dp(6))
        kwargs.setdefault("padding",[dp(10),dp(10),dp(10),dp(10)])
        super().__init__(**kwargs)
        self.app = app
        self._build()

    def _card(self, widget, height=None):
        wrap = BoxLayout(size_hint=(1,None), height=height or widget.height)
        with wrap.canvas.before:
            Color(*C["card"])
            self._rr = RoundedRectangle(pos=wrap.pos, size=wrap.size, radius=[dp(6)])
        def _upd(w,*_): w.canvas.before.children[-1].pos=w.pos; w.canvas.before.children[-1].size=w.size
        wrap.bind(pos=_upd, size=_upd)
        wrap.add_widget(widget)
        return wrap

    def _section_label(self, text):
        l = Label(text=text, font_size=sp(9), bold=True, color=C["gold"],
                  size_hint=(1,None), height=dp(20), halign="left", valign="middle")
        l.bind(size=lambda w,s: setattr(w,"text_size",s))
        return l

    def _build(self):
        # Status bar
        self.status_lbl = Label(
            text="White to move", font_size=sp(14), bold=True,
            color=C["txt"], size_hint=(1,None), height=dp(50),
            halign="center", valign="middle",
        )
        self.status_lbl.bind(size=lambda w,s: setattr(w,"text_size",s))
        sw = BoxLayout(size_hint=(1,None), height=dp(50))
        with sw.canvas.before:
            Color(*C["card"])
            self._srr = RoundedRectangle(pos=sw.pos,size=sw.size,radius=[dp(6)])
        sw.bind(pos=lambda w,*_:(setattr(self._srr,"pos",w.pos)),
                size=lambda w,*_:(setattr(self._srr,"size",w.size)))
        sw.add_widget(self.status_lbl)
        self.add_widget(sw)

        # Buttons (Horizontal to save vertical space)
        btn_row = BoxLayout(size_hint=(1, None), height=dp(44), spacing=dp(6))
        btn_row.add_widget(make_btn("♟ New",  self.app.new_game))
        btn_row.add_widget(make_btn("↩ Undo", self.app.undo_move))
        btn_row.add_widget(make_btn("↪ Redo", self.app.redo_move))
        self.add_widget(btn_row)

        # Divider
        div = Widget(size_hint=(1,None), height=dp(1))
        with div.canvas: Color(*C["txt_dim"],0.4); Rectangle(pos=div.pos,size=div.size)
        div.bind(pos=lambda w,p:(w.canvas.clear(), Color(*C["txt_dim"],0.4).__class__, Rectangle(pos=p,size=w.size)))
        self.add_widget(div)

        # Captured
        self.add_widget(self._section_label("CAPTURED"))
        cap_row = BoxLayout(size_hint=(1, None), height=dp(26), spacing=dp(6))
        self.cap_w = Label(text="W: —", font_size=sp(11), color=C["txt"],
                           size_hint=(1,1), halign="left", valign="middle")
        self.cap_w.bind(size=lambda w,s: setattr(w,"text_size",s))
        self.cap_b = Label(text="B: —", font_size=sp(11), color=C["txt"],
                           size_hint=(1,1), halign="left", valign="middle")
        self.cap_b.bind(size=lambda w,s: setattr(w,"text_size",s))
        cap_row.add_widget(self.cap_w)
        cap_row.add_widget(self.cap_b)
        self.add_widget(cap_row)

        # Divider 2
        div2 = Widget(size_hint=(1,None), height=dp(1))
        with div2.canvas: Color(*C["txt_dim"],0.4); Rectangle(pos=div2.pos,size=div2.size)
        self.add_widget(div2)

        # Move history
        self.add_widget(self._section_label("MOVE HISTORY"))
        scroll = ScrollView(size_hint=(1,1), do_scroll_x=False)
        self.hist_box = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(1))
        self.hist_box.bind(minimum_height=self.hist_box.setter("height"))
        scroll.add_widget(self.hist_box)
        self.add_widget(scroll)

    def update(self, game):
        g = game; s = g.status; t = g.turn
        if s=="checkmate":
            w = "Black" if t=="white" else "White"
            txt = f"{w} wins!  Checkmate"; col = C["gold"]
        elif s=="stalemate":
            txt = "Draw — Stalemate"; col = C["gold"]
        elif s=="check":
            m = "White" if t=="white" else "Black"
            txt = f"{m} to move  ⚠ Check!"; col = C["red"]
        else:
            txt = ("White" if t=="white" else "Black")+" to move"; col = C["txt"]
        self.status_lbl.text  = txt
        self.status_lbl.color = col

        ORDER = ["queen","rook","bishop","knight","pawn"]
        SYMS  = {"white":{"queen":"Q","rook":"R","bishop":"B","knight":"N","pawn":"P"},
                 "black":{"queen":"q","rook":"r","bishop":"b","knight":"n","pawn":"p"}}
        def sym(pieces):
            s = sorted(pieces, key=lambda p: ORDER.index(p.kind))
            return " ".join(SYMS[p.color][p.kind] for p in s) or "—"
        self.cap_w.text = "White: " + sym(game.captured["white"])
        self.cap_b.text = "Black: " + sym(game.captured["black"])

        self.hist_box.clear_widgets()
        pairs = game.move_pairs()
        for num,w,b in pairs:
            is_last = (num==len(pairs))
            row = Label(
                text=f" {num:2}.  {w:<8} {b}",
                size_hint_y=None, height=dp(24), font_size=sp(11),
                color=C["gold"] if is_last else C["txt"],
                halign="left", valign="middle",
            )
            row.bind(size=lambda w,s: setattr(w,"text_size",s))
            self.hist_box.add_widget(row)


# ═══════════════════════════════════════════════════════════════════════════════
#  PROMOTION POPUP
# ═══════════════════════════════════════════════════════════════════════════════

def show_promo(color, callback):
    NAMES = ["Queen","Rook","Bishop","Knight"]
    KINDS = ["queen","rook","bishop","knight"]
    content = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(10))
    content.add_widget(Label(text="Promote pawn to:", font_size=sp(14), bold=True,
                             color=C["txt"], size_hint=(1,None), height=dp(30)))
    row = BoxLayout(spacing=dp(6), size_hint=(1,None), height=dp(80))
    popup = Popup(title="", separator_height=0,
                  size_hint=(None,None), size=(dp(320),dp(160)),
                  background_color=(*C["card"][:3],1))
    for kind,name in zip(KINDS,NAMES):
        b = Button(text=name, background_normal="",
                   background_color=(*C["bg"][:3],1),
                   color=(*C["txt"][:3],1), font_size=sp(13), bold=True)
        def _cb(k=kind):
            popup.dismiss(); callback(k)
        b.bind(on_release=lambda *_,k=kind: _cb(k))
        row.add_widget(b)
    content.add_widget(row)
    popup.content = content
    popup.open()


# ═══════════════════════════════════════════════════════════════════════════════
#  ROOT LAYOUT  — responsive portrait / landscape
# ═══════════════════════════════════════════════════════════════════════════════

class RootLayout(BoxLayout):
    def __init__(self, app_ref, **kwargs):
        super().__init__(**kwargs)
        self.app_ref = app_ref
        Window.bind(size=self._on_window_size)

    def _on_window_size(self, *_):
        self._relayout()

    def _relayout(self):
        w, h = Window.size
        portrait = h >= w
        self.clear_widgets()
        if portrait:
            self.orientation = "vertical"
            # Guarantee minimum height for the panel to avoid overlapping the board
            panel_min = dp(240)
            board_sz = min(w, h - panel_min)
            if board_sz < 0:
                board_sz = 0
            self.app_ref.board_widget.size_hint = (1, None)
            self.app_ref.board_widget.height    = board_sz
            self.app_ref.panel.size_hint        = (1, 1)
            self.app_ref.panel.width            = w
            self.add_widget(self.app_ref.board_widget)
            self.add_widget(self.app_ref.panel)
        else:
            self.orientation = "horizontal"
            panel_min = dp(280)
            board_sz = min(h, w - panel_min)
            if board_sz < 0:
                board_sz = 0
            self.app_ref.board_widget.size_hint = (None, 1)
            self.app_ref.board_widget.width     = board_sz
            self.app_ref.panel.size_hint        = (1, 1)
            self.add_widget(self.app_ref.board_widget)
            self.add_widget(self.app_ref.panel)
        self.app_ref.board_widget._redraw()


# ═══════════════════════════════════════════════════════════════════════════════
#  APP
# ═══════════════════════════════════════════════════════════════════════════════

class ChessApp(App):
    def build(self):
        self.title = "Chess"
        Window.clearcolor = (*C["bg"][:3], 1)

        self.game  = GameState()
        self.sel   = None
        self.valid = []

        self.board_widget = BoardWidget(app=self)
        self.panel        = SidePanel(app=self)

        root = RootLayout(app_ref=self, orientation="horizontal")

        # Add background to panel
        with self.panel.canvas.before:
            Color(*C["panel_bg"])
            self._pr = Rectangle(pos=self.panel.pos, size=self.panel.size)
        self.panel.bind(pos=lambda w,*_: setattr(self._pr,"pos",w.pos),
                        size=lambda w,*_: setattr(self._pr,"size",w.size))

        root._relayout()
        self.panel.update(self.game)
        return root

    # ── interaction ───────────────────────────────────────────────────────────
    def handle_click(self, r, c):
        g = self.game
        if g.status in ("checkmate","stalemate"): return
        clicked = g.board[r][c]
        if self.sel:
            if (r,c) in self.valid:
                if g.needs_promo(self.sel[0],self.sel[1],r):
                    fr,fc = self.sel; color = g.board[fr][fc].color
                    show_promo(color, lambda k: self._exec(self.sel,(r,c),k))
                else:
                    self._exec(self.sel,(r,c))
                return
            if clicked and clicked.color==g.turn:
                self.sel=(r,c); self.valid=g.get_legal(r,c)
                self.board_widget._redraw(); return
            self.sel=None; self.valid=[]; self.board_widget._redraw(); return
        if clicked and clicked.color==g.turn:
            self.sel=(r,c); self.valid=g.get_legal(r,c)
            self.board_widget._redraw()

    def _exec(self, f, t, promo=None):
        self.game.redo_stack.clear()
        self.game.move(f[0],f[1],t[0],t[1],promo)
        self.sel=None; self.valid=[]
        self.board_widget._redraw()
        self.panel.update(self.game)
        if self.game.status in ("checkmate","stalemate"):
            orig = list(self.panel.status_lbl.color)
            self.panel.status_lbl.color = C["gold"]
            Clock.schedule_once(lambda *_: setattr(self.panel.status_lbl,"color",orig), 0.6)

    def new_game(self):
        self.game=GameState(); self.sel=None; self.valid=[]
        self.board_widget._redraw(); self.panel.update(self.game)

    def undo_move(self):
        self.game.undo(); self.sel=None; self.valid=[]
        self.board_widget._redraw(); self.panel.update(self.game)

    def redo_move(self):
        self.game.redo(); self.sel=None; self.valid=[]
        self.board_widget._redraw(); self.panel.update(self.game)


if __name__ == "__main__":
    ChessApp().run()