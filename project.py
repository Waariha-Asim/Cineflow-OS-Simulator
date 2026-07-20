"""
CineFlow - Step 2 + Step 3 + Step 4: Priority Queue + Round Robin + Parallel Servers
=====================================================================================
Step 2: Priority Queue (VIP first)
Step 3: Round Robin (burst time + time quantum)
Step 4 (NEW):
  - BookingServer dataclass  : 3 alag servers, har ek ka apna queue
  - Load Balancing           : least busy server ko request assign hoti hai
  - Parallel Processing      : 3 threads ek saath chaltay hain
  - system_lock              : shared data ko protect karta hai (synchronization)
  - server_worker thread     : har server apna queue Round Robin se process karta hai

OS Concepts covered so far:
  Priority Scheduling | Round Robin | Parallel Processing | Load Balancing | Synchronization
"""

import tkinter as tk
from tkinter import ttk, messagebox
from dataclasses import dataclass, field
import time
import threading
import random
from collections import deque


# =============================================
# DATA MODEL (Step 1 se liya, same)
# =============================================

@dataclass(order=True)
class BookingRequest:
    sort_index: tuple = field(init=False, repr=False)

    priority: int
    arrival_order: int
    request_id: int
    name: str
    user_type: str              # "VIP" ya "Normal"
    movie: str
    seat_no: int
    burst_time: int = 3         # Step 3: total CPU time needed
    status: str = "Waiting"
    arrival_time: float = field(default_factory=time.time)
    remaining_time: int = field(init=False, compare=False)  # Step 3: kitna bacha hai

    def __post_init__(self):
        """Naya request bante hi sort key aur remaining time set karta hai."""
        self.sort_index = (self.priority, self.arrival_order)
        self.remaining_time = self.burst_time   # shuru mein remaining = burst


# =============================================
# PRIORITY QUEUE CLASS  <- Step 2 ka main addition
# =============================================

class PriorityQueue:
    """
    OS Concept: Priority Scheduling

    Andar ek simple Python list hai.
    Har insert ke baad list sort hoti hai sort_index se.

    sort_index = (priority, arrival_order)
    -> VIP    : (1, 1), (1, 3), (1, 5)  <- hamesha top pe
    -> Normal : (2, 2), (2, 4), (2, 6)  <- VIP ke baad

    Same priority mein arrival_order decide karta hai (FCFS).
    """

    def __init__(self):
        """Khali queue banata hai jahan requests store hongi."""
        self._queue = []           # internal list
        self._arrival_counter = 0  # FCFS order track karne ke liye

    def enqueue(self, request: BookingRequest):
        """Request add karke queue ko priority/arrival order se sort karta hai."""
        self._queue.append(request)
        # Sort karta hai priority k according 
        #lambda ek anonymous function hai jo har request ke sort_index ko return karta hai, jisse queue sort hoti hai.
        self._queue.sort(key=lambda r: r.sort_index)   # Priority Scheduling sort

    def dequeue(self) -> BookingRequest | None:
        """Queue ka sab se pehla (highest priority) request nikalta hai."""
        if self._queue:
            return self._queue.pop(0)
        return None

    def peek(self) -> BookingRequest | None:
        """Next request batata hai bina queue se remove kiye."""
        return self._queue[0] if self._queue else None

    def is_empty(self) -> bool:
        """Check karta hai queue khali hai ya nahi."""
        return len(self._queue) == 0

    def size(self) -> int:
        """Queue mein total requests ki tadaad return karta hai."""
        return len(self._queue)

    def all_requests(self) -> list:
        """UI refresh ke liye queue ka safe copy deta hai."""
        return list(self._queue)


# =============================================
# BOOKING SERVER  (Step 4)
# =============================================

@dataclass
class BookingServer:
    server_id: int
    queue: deque = field(default_factory=deque)   # is server ka apna request queue
    processed_count: int = 0                       # kitne complete hue
    total_busy: int = 0                            # total units processed


# ----------------------------------
# -----------
# Shared style helper (tamam windows yahi style use karti hain)
# ---------------------------------------------
MOVIES = ["Inception", "The Dark Knight", "Interstellar",
          "The Matrix", "Avengers: Endgame", "Titanic"]

BG      = "#101827"
PANEL   = "#172033"
CARD    = "#1f2a44"
PURPLE  = "#7c3aed"
PURPLL  = "#c4b5fd"
GREEN   = "#16a34a"
RED     = "#dc2626"
BLUE    = "#2563eb"
CYAN    = "#0891b2"
YELLOW  = "#facc15"
MINT    = "#6ee7b7"
GRAY    = "#9ca3af"


def _apply_style():
    """Treeview aur headings ki common styling set karta hai."""
    s = ttk.Style()
    s.theme_use("clam")
    # configure kisi GUI element label textbox button ki properties change/update karta hai.
    s.configure("Treeview", background=PANEL, foreground="white",
                fieldbackground=PANEL, rowheight=28, font=("Calibri", 10))
    s.configure("Treeview.Heading", background=PURPLE, foreground="white",
                font=("Calibri", 10, "bold"))
    s.map("Treeview", background=[("selected", PURPLE)])


def _mktree(parent, cols, widths, height=7):
    """Given columns ke sath ek styled table banata hai."""
    t = ttk.Treeview(parent, columns=cols, show="headings", height=height)
    for col in cols:
        t.heading(col, text=col)
        t.column(col, width=widths.get(col, 90))
    t.tag_configure("vip",    background="#3b1f6e", foreground="#e9d5ff")
    t.tag_configure("normal", background=PANEL,     foreground="white")
    t.tag_configure("done",   background="#14532d", foreground="#bbf7d0")
    t.tag_configure("active", background="#1e3a5f", foreground="#bfdbfe")
    t.tag_configure("idle",   background=PANEL,     foreground="#6b7280")
    t.pack(fill=tk.BOTH, expand=True, padx=5, pady=4)
    return t


def _lbl(parent, text):
    """Form ke liye standard label banata hai."""
    tk.Label(parent, text=text, bg=PANEL, fg="#e5e7eb",
             font=("Calibri", 10, "bold")).pack(anchor="w", padx=14, pady=(7, 2))


def _entry(parent):
    """Form ka standard text entry field return karta hai."""
    e = tk.Entry(parent, font=("Calibri", 11), bg=CARD, fg="white",
                 insertbackground="white", relief="flat")
    e.pack(fill=tk.X, padx=14)
    return e


def _combo(parent, var, values):
    """Readonly dropdown banata hai aur return karta hai."""
    c = ttk.Combobox(parent, textvariable=var, values=values,
                     state="readonly", font=("Calibri", 11))
    c.pack(fill=tk.X, padx=14)
    return c


def _spin(parent, lo, hi, default):
    """Numeric input ke liye spinbox banata hai."""
    s = tk.Spinbox(parent, from_=lo, to=hi, font=("Calibri", 11),
                   bg=CARD, fg="white", buttonbackground=PURPLE, relief="flat")
    s.delete(0, tk.END)
    s.insert(0, str(default))
    s.pack(fill=tk.X, padx=14)
    return s


def _btn(parent, text, cmd, color=PURPLE):
    """Standard styled button banata hai aur return karta hai."""
    b = tk.Button(parent, text=text, command=cmd, bg=color, fg="white",
                  activebackground="#a78bfa", relief="flat",
                  font=("Calibri", 10, "bold"), padx=10, pady=7, cursor="hand2")
    b.pack(fill=tk.X, padx=14, pady=3)
    return b


# =============================================
# WINDOW 1 - PRIORITY QUEUE  (Step 2)
# =============================================

class PriorityQueueWindow:
    """
    Sirf Priority Scheduling.
    Koi burst time nahi, koi threading nahi.
    Dekhte hain VIP kaise Normal se pehle jaata hai.
    """
    def __init__(self, root):
        """Yeh constructor class ka initial setup karta hai."""
        self.root = root
        self.root.title("Step 1 - Priority Queue")
        self.root.geometry("860x470")
        self.root.configure(bg=BG)
        _apply_style()

        self.pq       = PriorityQueue()
        self.arrival  = 0
        self.req_id   = 1
        self.done     = []
        self._build()

    def _build(self):
        """Yeh function UI layout aur controls banata hai."""
        # Header bar
        hdr = tk.Frame(self.root, bg=PURPLE, height=46)
        hdr.pack(fill=tk.X);  hdr.pack_propagate(False)
        tk.Label(hdr, text="Step 1 - Priority Queue  |  OS Concept: Priority Scheduling",
                 font=("Calibri", 12, "bold"), bg=PURPLE, fg="white").pack(side=tk.LEFT, padx=14)

        body = tk.Frame(self.root, bg=BG)
        body.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Baayen side form
        form = tk.Frame(body, bg=PANEL, width=240)
        form.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        form.pack_propagate(False)

        tk.Label(form, text="Add Request", font=("Calibri", 13, "bold"),
                 bg=PANEL, fg=PURPLL).pack(pady=(12, 6))
        _lbl(form, "Customer Name:");  self.nm = _entry(form)
        _lbl(form, "User Type:")
        #lbl koi dropdown banata hai aur uska variable return karta hai jisme selected value store hoti hai.
        self.tv = tk.StringVar(value="Normal");  _combo(form, self.tv, ["VIP", "Normal"])
        _lbl(form, "Movie:")
        #tk.stringvar ek variable class hai jo tkinter widgets ke sath use hota hai, jisme current value store hoti hai aur widget usko update karta hai.
        self.mv = tk.StringVar(value=MOVIES[0]); _combo(form, self.mv, MOVIES)
        _lbl(form, "Seat (1-50):");  self.ss = _spin(form, 1, 50, 1)

        _btn(form, "Add to Priority Queue", self._add, PURPLE)
        _btn(form, "Process Next (Dequeue)", self._process, GREEN)

        self.sz = tk.Label(form, text="Queue: 0", font=("Calibri", 11, "bold"),
                           bg=PANEL, fg=YELLOW)
        self.sz.pack(pady=6)
        tk.Label(form, text="VIP  -> priority 1  (top)\nNormal -> priority 2\nSame priority -> FCFS order",
                 bg=PANEL, fg=MINT, font=("Calibri", 9), justify="left").pack(padx=14, anchor="w")

        # Daayen side tables
        right = tk.Frame(body, bg=BG)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tk.Label(right, text="Priority Queue  (VIP rows = purple)",
                 bg=BG, fg=PURPLL, font=("Calibri", 11, "bold")).pack(anchor="w")
        self.qt = _mktree(right,
            ("ID", "Name", "User Type", "Priority", "Movie", "Seat", "Status"),
            {"ID": 40, "Name": 115, "User Type": 85, "Priority": 70,
             "Movie": 135, "Seat": 55, "Status": 90}, height=7)
        tk.Label(right, text="Processed", bg=BG, fg=MINT,
                 font=("Calibri", 11, "bold")).pack(anchor="w", pady=(10, 0))
        self.pt = _mktree(right,
            ("ID", "Name", "User Type", "Priority", "Movie", "Seat", "Status"),
            {"ID": 40, "Name": 115, "User Type": 85, "Priority": 70,
             "Movie": 135, "Seat": 55, "Status": 90}, height=5)

    def _seat_owner(self, seat):
        """Yeh function di gayi seat ka current owner return karta hai."""
        for r in self.pq.all_requests() + self.done:
            if r.seat_no == seat:
                return r.name
        return None

    def _add(self):
        """Yeh function user input se request add karta hai."""
        name = self.nm.get().strip()
        if not name:
            messagebox.showerror("Error", "Name required.", parent=self.root); return
        try:
            seat = int(self.ss.get().replace(",", ""))
        except ValueError:
            messagebox.showerror("Invalid Seat", "Seat number must be a valid integer between 1 and 50.", parent=self.root)
            return
        if not 1 <= seat <= 50:
            messagebox.showerror("Invalid Seat", "Seat number must be between 1 and 50.", parent=self.root)
            return
        owner = self._seat_owner(seat)
        if owner:
            messagebox.showerror("Seat Taken",
                                 f"Seat {seat} already assigned to '{owner}'.",
                                 parent=self.root); return
        ut = self.tv.get()
        self.arrival += 1
        req = BookingRequest(priority=1 if ut == "VIP" else 2,
                             arrival_order=self.arrival, request_id=self.req_id,
                             name=name, user_type=ut,
                             movie=self.mv.get(), seat_no=seat)
        self.req_id += 1
        self.pq.enqueue(req)
        print(f"[PQ] #{req.request_id} {req.name} ({ut})  sort_index={req.sort_index}")
        self.nm.delete(0, tk.END)
        self._refresh()

    def _process(self):
        """Yeh function _process ka specific kaam handle karta hai."""
        if self.pq.is_empty():
            messagebox.showinfo("Empty", "Queue is empty.", parent=self.root); return
        req = self.pq.dequeue()
        req.status = "Processed"
        self.done.append(req)
        print(f"[PQ] Processed #{req.request_id} {req.name} ({req.user_type})")
        self._refresh()

    def _refresh(self):
        """Yeh function UI tables ko latest data se update karta hai."""
        for t in (self.qt, self.pt):
            for i in t.get_children(): t.delete(i)
        for r in self.pq.all_requests():
            self.qt.insert("", tk.END, tags=("vip" if r.user_type == "VIP" else "normal",),
                           values=(r.request_id, r.name, r.user_type,
                                   r.priority, r.movie, r.seat_no, r.status))
        for r in self.done:
            self.pt.insert("", tk.END, tags=("done",),
                           values=(r.request_id, r.name, r.user_type,
                                   r.priority, r.movie, r.seat_no, r.status))
        self.sz.config(text=f"Queue: {self.pq.size()}")


# =============================================
# WINDOW 2 - ROUND ROBIN  (Step 3)
# =============================================

class RoundRobinWindow:
    """
    Sirf Round Robin Scheduling.
    Ek queue, manual cycle button, no threading.
    Burst/Remaining columns se progress clearly dikhti hai.
    """
    def __init__(self, root):
        """Yeh constructor class ka initial setup karta hai."""
        self.root = root
        self.root.title("Step 2 - Round Robin Scheduling")
        self.root.geometry("940x510")
        self.root.configure(bg=BG)
        _apply_style()

        self.pq           = PriorityQueue()
        self.arrival      = 0
        self.req_id       = 1
        self.done         = []
        self.time_quantum = 2
        self._build()

    def _build(self):
        """Yeh function UI layout aur controls banata hai."""
        #hdr kisi section ka header banata hai, jisme title aur OS concept show hota hai.
        hdr = tk.Frame(self.root, bg=GREEN, height=46)
        #pack_propagate false karta hai jisme children ka size update nahi hota hai.
        hdr.pack(fill=tk.X);  hdr.pack_propagate(False)
        tk.Label(hdr, text="Step 2 - Round Robin  |  OS Concept: Fair CPU Time Slicing",
                 font=("Calibri", 12, "bold"), bg=GREEN, fg="white").pack(side=tk.LEFT, padx=14)

        body = tk.Frame(self.root, bg=BG)
        body.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Baayen side form with vertical scrollbar
        form_outer = tk.Frame(body, bg=PANEL, width=265)
        form_outer.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        form_outer.pack_propagate(False)

        form_canvas = tk.Canvas(form_outer, bg=PANEL, highlightthickness=0)
        form_scroll = ttk.Scrollbar(form_outer, orient="vertical", command=form_canvas.yview)
        form = tk.Frame(form_canvas, bg=PANEL)

        form.bind("<Configure>", lambda e: form_canvas.configure(scrollregion=form_canvas.bbox("all")))
        form_canvas.create_window((0, 0), window=form, anchor="nw")
        form_canvas.configure(yscrollcommand=form_scroll.set)

        form_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        form_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        tk.Label(form, text="Add Request", font=("Calibri", 13, "bold"),
                 bg=PANEL, fg=PURPLL).pack(pady=(12, 6))
        _lbl(form, "Customer Name:");  self.nm = _entry(form)
        _lbl(form, "User Type:")
        self.tv = tk.StringVar(value="Normal"); _combo(form, self.tv, ["VIP", "Normal"])
        _lbl(form, "Movie:")
        self.mv = tk.StringVar(value=MOVIES[0]); _combo(form, self.mv, MOVIES)
        _lbl(form, "Seat (1-50):");  self.ss = _spin(form, 1, 50, 1)
        _lbl(form, "Burst Time (1-10):"); self.bs = _spin(form, 1, 10, 4)

        _btn(form, "Add to Queue", self._add, PURPLE)
        _btn(form, "Generate Random Request", self._generate_random, BLUE)

        # Quantum control
        qf = tk.LabelFrame(form, text="Time Quantum", bg=PANEL, fg=YELLOW,
                           font=("Calibri", 9, "bold"))
        qf.pack(fill=tk.X, padx=14, pady=6)
        self.qs = tk.Spinbox(qf, from_=1, to=10, font=("Calibri", 11),
                             bg=CARD, fg="white", buttonbackground=PURPLE,
                             relief="flat", width=5)
        self.qs.delete(0, tk.END);  self.qs.insert(0, "2")
        self.qs.pack(side=tk.LEFT, padx=8, pady=5)
        tk.Button(qf, text="Apply", bg=BLUE, fg="white", relief="flat",
                  font=("Calibri", 9, "bold"), cursor="hand2",
                  command=self._applyq).pack(side=tk.LEFT, padx=4, pady=5)
        self.ql = tk.Label(qf, text="Q=2", bg=PANEL, fg=YELLOW,
                           font=("Calibri", 10, "bold"))
        self.ql.pack(side=tk.LEFT, padx=4)

        _btn(form, "Run One RR Cycle", self._cycle, GREEN)
        _btn(form, "Reset RR", self._reset_rr, RED)

        self.sz = tk.Label(form, text="Queue: 0", font=("Calibri", 11, "bold"),
                           bg=PANEL, fg=YELLOW)
        self.sz.pack(pady=5)
        tk.Label(form,
                 text="Burst = total CPU needed\nRemaining = kitna bacha\nQuantum = ek baar kitna\nRe-queued if remaining > 0",
                 bg=PANEL, fg=MINT, font=("Calibri", 9), justify="left").pack(padx=14, anchor="w")

        # Daayen side tables with vertical scrollbar
        right_outer = tk.Frame(body, bg=BG)
        right_outer.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        right_canvas = tk.Canvas(right_outer, bg=BG, highlightthickness=0)
        right_scroll = ttk.Scrollbar(right_outer, orient="vertical", command=right_canvas.yview)
        right = tk.Frame(right_canvas, bg=BG)

        right.bind("<Configure>", lambda e: right_canvas.configure(scrollregion=right_canvas.bbox("all")))
        right_canvas.create_window((0, 0), window=right, anchor="nw")
        right_canvas.configure(yscrollcommand=right_scroll.set)

        right_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        right_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        tk.Label(right, text="Round Robin Queue  (watch Remaining decrease per cycle)",
                 bg=BG, fg=PURPLL, font=("Calibri", 11, "bold")).pack(anchor="w")
        self.qt = _mktree(right,
            ("ID", "Name", "Type", "Priority", "Movie", "Seat", "Burst", "Remaining", "Status"),
            {"ID": 40, "Name": 100, "Type": 70, "Priority": 65,
             "Movie": 115, "Seat": 50, "Burst": 55, "Remaining": 80, "Status": 95}, height=7)
        tk.Label(right, text="Processed", bg=BG, fg=MINT,
                 font=("Calibri", 11, "bold")).pack(anchor="w", pady=(10, 0))
        self.pt = _mktree(right,
            ("ID", "Name", "Type", "Priority", "Movie", "Seat", "Burst", "Status"),
            {"ID": 40, "Name": 100, "Type": 70, "Priority": 65,
             "Movie": 115, "Seat": 50, "Burst": 55, "Status": 90}, height=5)

        tk.Label(right, text="Activity Log", bg=BG, fg=YELLOW,
                 font=("Calibri", 11, "bold")).pack(anchor="w", pady=(10, 0))
        log_frame = tk.Frame(right, bg=BG)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(4, 0))
        self.log_box = tk.Text(log_frame, height=8, bg=CARD, fg="white",
                               font=("Calibri", 9), relief="flat",
                               state=tk.DISABLED, wrap=tk.WORD)
        log_scroll = ttk.Scrollbar(log_frame, command=self.log_box.yview)
        self.log_box.configure(yscrollcommand=log_scroll.set)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_box.pack(fill=tk.BOTH, expand=True)

        def _bind_mousewheel(widget, canvas):
            widget.bind("<Enter>", lambda _e: canvas.bind_all("<MouseWheel>", lambda event: canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")))
            widget.bind("<Leave>", lambda _e: canvas.unbind_all("<MouseWheel>"))

        _bind_mousewheel(form, form_canvas)
        _bind_mousewheel(right, right_canvas)

        self.log_box.tag_configure("info", foreground="#93c5fd")
        self.log_box.tag_configure("ok", foreground=MINT)
        self.log_box.tag_configure("warn", foreground="#fbbf24")

    def _log(self, message, tag="info"):
        """Yeh function activity log mein message show karta hai."""
        self.log_box.configure(state=tk.NORMAL)
        self.log_box.insert(tk.END, message + "\n", tag)
        self.log_box.see(tk.END)
        self.log_box.configure(state=tk.DISABLED)

    def _applyq(self):
        """Yeh function RR quantum value validate karke apply karta hai."""
        try:
            v = int(self.qs.get())
            if v < 1: raise ValueError
            self.time_quantum = v
            self.ql.config(text=f"Q={v}")
            print(f"[RR] Quantum -> {v}")
            self._log(f"Quantum updated to {v}", "ok")
        except ValueError:
            messagebox.showerror("Error", "Quantum must be positive.", parent=self.root)

    def _seat_owner(self, seat):
        """Yeh function di gayi seat ka current owner return karta hai."""
        for r in self.pq.all_requests() + self.done:
            if r.seat_no == seat: return r.name
        return None

    def _generate_random(self):
        """Yeh function random request bana kar queue mein add karta hai."""
        available_seats = [s for s in range(1, 51) if self._seat_owner(s) is None]
        if not available_seats:
            messagebox.showinfo("Full", "No free seats available.", parent=self.root)
            return

        sample_names = ["Ali", "Sara", "Hani", "Bilal", "Ayesha", "Hamza", "Noor", "Zain"]
        name = f"{random.choice(sample_names)}{random.randint(1, 99)}"
        ut = random.choice(["VIP", "Normal"])
        seat = random.choice(available_seats)
        burst = random.randint(1, 10)

        self.arrival += 1
        req = BookingRequest(priority=1 if ut == "VIP" else 2,
                             arrival_order=self.arrival, request_id=self.req_id,
                             name=name, user_type=ut,
                             movie=random.choice(MOVIES), seat_no=seat, burst_time=burst)
        self.req_id += 1
        self.pq.enqueue(req)

        self._log(
            f"Random request added #{req.request_id}: {req.name} ({ut}) | Seat {seat} | Burst {burst}",
            "ok"
        )
        self._refresh()

    def _reset_rr(self):
        """Yeh function Round Robin section ko reset karta hai."""
        self.pq = PriorityQueue()
        self.done = []
        self.arrival = 0
        self.req_id = 1
        self.nm.delete(0, tk.END)

        self.log_box.configure(state=tk.NORMAL)
        self.log_box.delete("1.0", tk.END)
        self.log_box.configure(state=tk.DISABLED)

        self._refresh()
        self._log("Round Robin state reset: queue and processed data cleared.", "info")

    def _add(self):
        """Yeh function user input se request add karta hai."""
        name = self.nm.get().strip()
        if not name:
            messagebox.showerror("Error", "Name required.", parent=self.root); return
        try:
            seat = int(self.ss.get().replace(",", ""))
        except ValueError:
            messagebox.showerror("Invalid Seat", "Seat number must be a valid integer between 1 and 50.", parent=self.root)
            return
        if not 1 <= seat <= 50:
            messagebox.showerror("Invalid Seat", "Seat number must be between 1 and 50.", parent=self.root)
            return
        owner = self._seat_owner(seat)
        if owner:
            messagebox.showerror("Seat Taken",
                                 f"Seat {seat} already assigned to '{owner}'.",
                                 parent=self.root); return
        ut = self.tv.get()
        self.arrival += 1
        burst = int(self.bs.get().replace(",", ""))
        req = BookingRequest(priority=1 if ut == "VIP" else 2,
                             arrival_order=self.arrival, request_id=self.req_id,
                             name=name, user_type=ut,
                             movie=self.mv.get(), seat_no=seat, burst_time=burst)
        self.req_id += 1
        self.pq.enqueue(req)
        print(f"[RR] #{req.request_id} {req.name} burst={burst} sort_index={req.sort_index}")
        self._log(f"Added request #{req.request_id}: {req.name} ({ut}) | Seat {seat} | Burst {burst}")
        self.nm.delete(0, tk.END)
        self._refresh()

    def _cycle(self):
        """Yeh function Round Robin ka aik cycle execute karta hai."""
        if self.pq.is_empty():
            messagebox.showinfo("Empty", "Queue is empty.", parent=self.root); return
        req = self.pq.dequeue() #queue se next request nikalta hai
        ex = min(self.time_quantum, req.remaining_time) #cpu jitna kaam ho tq ya rt utna hi run krega
        req.remaining_time -= ex
        print(f"[RR] #{req.request_id} {req.name}  exec={ex}  remaining={req.remaining_time}/{req.burst_time}")
        self._log(f"Processing #{req.request_id}: {req.name} | ran {ex} unit(s) | remaining {req.remaining_time}/{req.burst_time}")
        #agr kaam bacha hai to wapas queue mein daal do warna complete mark kar do
        if req.remaining_time > 0:
            req.status = "Re-queued"
            self.arrival += 1
            req.arrival_order = self.arrival
            req.sort_index = (req.priority, req.arrival_order)
            self.pq.enqueue(req)
            print(f"  -> Re-queued (remaining={req.remaining_time})")
            self._log(f"Request #{req.request_id} re-queued with {req.remaining_time} unit(s) remaining", "warn")
        else:
            req.status = "Processed"
            self.done.append(req)
            print(f"  -> COMPLETED")
            self._log(f"Request #{req.request_id} completed", "ok")
        self._refresh()

    def _refresh(self):
        """Yeh function UI tables ko latest data se update karta hai."""
        for t in (self.qt, self.pt):
            for i in t.get_children(): t.delete(i)
        for r in self.pq.all_requests():
            self.qt.insert("", tk.END, tags=("vip" if r.user_type == "VIP" else "normal",),
                           values=(r.request_id, r.name, r.user_type, r.priority,
                                   r.movie, r.seat_no, r.burst_time, r.remaining_time, r.status))
        for r in self.done:
            self.pt.insert("", tk.END, tags=("done",),
                           values=(r.request_id, r.name, r.user_type, r.priority,
                                   r.movie, r.seat_no, r.burst_time, r.status))
        self.sz.config(text=f"Queue: {self.pq.size()}")
        self.root.update_idletasks()


# =============================================
# WINDOW 4 - SEAT LOCKING
# =============================================

class SeatLockingWindow:
    """
    Step 4 - Critical Section + Seat Locking
    OS Concepts:
    cs: code ka woh part jahan shared resource access hota hai, jise ek waqt mein sirf ek thread access kar sakta hai.
      - Critical Section : ek waqt mein sirf ek thread seat book kar sakta hai
      - per-seat Lock    : seat_locks[seat_no] = threading.Lock()
    - Non-blocking try : acquire(blocking=False) - rejection instead of deadlock
      - Resource Alloc   : seats as shared resources, 3 servers as threads
    Demo:
      - 20 seats shown as coloured grid (Green=Free, Yellow=Locked, Red=Booked)
      - "Start 3-Server Race" : 3 threads simultaneously try random seats
      - You can also manually try to book a locked seat to see rejection
    """
    SEATS     = 20
    COLORS    = {"Free": "#16a34a", "Locked": "#ca8a04", "Booked": "#7c3aed"}
    TXT_CLR   = {"Free": "white",   "Locked": "black",   "Booked": "white"}

    def __init__(self, root):
        """Yeh constructor class ka initial setup karta hai."""
        self.root = root
        self.root.title("Step 3 - Seat Locking (Critical Section)")
        self.root.geometry("900x560")
        self.root.configure(bg=BG)
        _apply_style()

        # Har seat ka apna lock (Critical Section)
        self.seat_locks  = {i: threading.Lock() for i in range(1, self.SEATS + 1)}
        self.seat_status = {i: "Free"  for i in range(1, self.SEATS + 1)}  # Free/Locked/Booked
        self.seat_owner  = {i: ""      for i in range(1, self.SEATS + 1)}
        self.log_lines   = []
        self.running     = False
        self._btns       = {}
        self._build()

    # UI section
    def _build(self):
        """Yeh function UI layout aur controls banata hai."""
        hdr = tk.Frame(self.root, bg="#7e22ce", height=46)
        hdr.pack(fill=tk.X); hdr.pack_propagate(False)
        tk.Label(hdr,
                 text="Step 3 - Seat Locking  |  OS Concept: Critical Section + Synchronization",
                 font=("Calibri", 12, "bold"), bg="#7e22ce", fg="white").pack(side=tk.LEFT, padx=14)

        body = tk.Frame(self.root, bg=BG)
        body.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # LEFT: controls aur legend
        ctrl = tk.Frame(body, bg=PANEL, width=255)
        ctrl.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        ctrl.pack_propagate(False)

        tk.Label(ctrl, text="Seat Locking Demo", font=("Calibri", 13, "bold"),
                 bg=PANEL, fg="#c084fc").pack(pady=(12, 6))

        # Manual booking form
        _lbl(ctrl, "Your Name:")
        self.nm = _entry(ctrl)
        _lbl(ctrl, "Seat Number (1-20):")
        self.ss = _spin(ctrl, 1, 20, 1)
        _btn(ctrl, "Try to Book Seat", self._manual_book, "#7e22ce")

        tk.Frame(ctrl, bg="#374151", height=1).pack(fill=tk.X, padx=14, pady=8)

        _btn(ctrl, "Start 3-Server Race", self._start_race, CYAN)
        _btn(ctrl, "Reset All Seats",     self._reset,      RED)

        # Legend
        tk.Label(ctrl, text="Legend:", font=("Calibri", 10, "bold"),
                 bg=PANEL, fg=GRAY).pack(anchor="w", padx=14, pady=(10, 2))
        for state, color in self.COLORS.items():
            f = tk.Frame(ctrl, bg=PANEL)
            f.pack(anchor="w", padx=14, pady=1)
            tk.Label(f, bg=color, width=3, height=1).pack(side=tk.LEFT, padx=(0, 6))
            tk.Label(f, text=state, bg=PANEL, fg="#e5e7eb",
                     font=("Calibri", 10)).pack(side=tk.LEFT)

        tk.Label(ctrl,
                 text="\nseat_locks[seat_no]\n  = threading.Lock()\n\n"
                      "acquire(blocking=False)\n  True  -> Critical Section\n"
                      "  False -> Seat is Locked!\n\nrelease() after booking",
                 bg=PANEL, fg=MINT, font=("Calibri", 9), justify="left").pack(padx=14, anchor="w")

        # RIGHT: seat grid aur activity log
        right = tk.Frame(body, bg=BG)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        tk.Label(right, text="Seat Grid  (20 seats - watch colours change in real time)",
                 bg=BG, fg="#c084fc", font=("Calibri", 11, "bold")).pack(anchor="w")

        grid_frame = tk.Frame(right, bg=BG)
        grid_frame.pack(fill=tk.X, pady=6)
        for seat in range(1, self.SEATS + 1):
            row, col = (seat - 1) // 5, (seat - 1) % 5
            btn = tk.Button(grid_frame, text=f"S{seat}", width=7, height=2,
                            bg=self.COLORS["Free"], fg="white",
                            font=("Calibri", 9, "bold"), relief="flat",
                            command=lambda s=seat: self._seat_click(s))
            btn.grid(row=row, column=col, padx=4, pady=4)
            self._btns[seat] = btn

        tk.Label(right, text="Activity Log", bg=BG, fg=YELLOW,
                 font=("Calibri", 11, "bold")).pack(anchor="w", pady=(10, 2))

        log_frame = tk.Frame(right, bg=BG)
        log_frame.pack(fill=tk.BOTH, expand=True)
        self.log_box = tk.Text(log_frame, height=10, bg=CARD, fg="white",
                               font=("Calibri", 9), relief="flat",
                               state=tk.DISABLED, wrap=tk.WORD)
        sb = ttk.Scrollbar(log_frame, command=self.log_box.yview)
        self.log_box.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_box.pack(fill=tk.BOTH, expand=True)

        # colour tags for log
        self.log_box.tag_configure("ok",      foreground=MINT)
        self.log_box.tag_configure("reject",  foreground="#f87171")
        self.log_box.tag_configure("lock",    foreground=YELLOW)
        self.log_box.tag_configure("info",    foreground=GRAY)

    # Helper methods
    def _log(self, msg, tag="info"):
        """Yeh function activity log mein message show karta hai."""
        self.root.after(0, lambda: self._write_log(msg, tag))

    def _write_log(self, msg, tag):
        """Yeh function _write_log ka specific kaam handle karta hai."""
        self.log_box.configure(state=tk.NORMAL)
        self.log_box.insert(tk.END, msg + "\n", tag)
        self.log_box.see(tk.END)
        self.log_box.configure(state=tk.DISABLED)

    def _update_seat_ui(self, seat):
        """Yeh function ek seat ka UI color aur label update karta hai."""
        state = self.seat_status[seat]
        owner = self.seat_owner[seat]
        label = f"S{seat}\n{owner[:6]}" if owner else f"S{seat}"
        self._btns[seat].config(
            bg=self.COLORS[state],
            fg=self.TXT_CLR[state],
            text=label)

    def _refresh_grid(self):
        """Yeh function poori seat grid ko refresh karta hai."""
        for seat in range(1, self.SEATS + 1):
            self._update_seat_ui(seat)

    # Manual booking section
    def _seat_click(self, seat):
        """Yeh function clicked seat number ko input mein set karta hai."""
        self.ss.delete(0, tk.END)
        self.ss.insert(0, str(seat))

    def _manual_book(self):
        """Yeh function manual booking request process karta hai."""
        name = self.nm.get().strip()
        if not name:
            messagebox.showerror("Error", "Name required.", parent=self.root); return
        seat = int(self.ss.get().replace(",", ""))
        self._try_book(seat, name, "You")

    def _try_book(self, seat, name, server_label):
        """
        Critical Section demo:
        acquire(blocking=False) -> non-blocking try.
        Returns True (got lock) or False (seat already locked).
        """
        lock = self.seat_locks[seat]
        acquired = lock.acquire(blocking=False)   # core OS concept

        if not acquired:
            # Kisi aur thread ne lock hold kiya hua hai
            self._log(f"[{server_label}] REJECTED - Seat {seat} is "
                      f"{self.seat_status[seat]} by '{self.seat_owner[seat]}'", "reject")
            return False

#Critical section wo code hota hai jahan shared resource (seat) 
# modify hota hai, aur lock is liye lagaya jata hai taake ek waqt me sirf ek thread us resource ko use kare
        # --- Critical section ke andar ---
        try:
            if self.seat_status[seat] == "Booked":
                self._log(f"[{server_label}] REJECTED - Seat {seat} already Booked "
                          f"by '{self.seat_owner[seat]}'", "reject")
                return False

            # Mark Locked while processing
            self.seat_status[seat] = "Locked"
            self.seat_owner[seat]  = name
            self.root.after(0, lambda s=seat: self._update_seat_ui(s))
            self._log(f"[{server_label}] LOCKED   Seat {seat} - processing...", "lock")

            time.sleep(0.8)   # simulate booking time (critical section duration)

            # Confirm booking
            self.seat_status[seat] = "Booked"
            self.root.after(0, lambda s=seat: self._update_seat_ui(s))
            self._log(f"[{server_label}] BOOKED   Seat {seat} for '{name}' OK", "ok")
            return True
        finally:
            lock.release()    # hamesha release karo, error par bhi
        # --- Critical section end ---

    # --- 3-Server Race ---
    def _start_race(self):
        """Yeh function 3-server race demo start karta hai."""
        if self.running:
            messagebox.showinfo("Running", "Race already in progress.", parent=self.root); return
        self.running = True
        self._log("--- 3-Server Race Started --- (servers try overlapping seats)", "info")

        import random
        # Each server tries to book 4 random seats (intentional overlaps possible)
        bookings = {
            "Server-1": random.sample(range(1, self.SEATS + 1), 5),
            "Server-2": random.sample(range(1, self.SEATS + 1), 5),
            "Server-3": random.sample(range(1, self.SEATS + 1), 5),
        }
        # Show which seats each server will attempt
        for srv, seats in bookings.items():
            self._log(f"  {srv} will attempt seats: {seats}", "info")

        names = {"Server-1": "Alice", "Server-2": "Bob", "Server-3": "Carol"}

        def worker(label, seat_list):
            """Yeh function worker ka specific kaam handle karta hai."""
            for seat in seat_list:
                if self.seat_status[seat] != "Booked":
                    self._try_book(seat, names[label], label)
                    time.sleep(0.1)
            self._log(f"  {label} finished all attempts.", "info")

        threads = []
        for label, seat_list in bookings.items():
            t = threading.Thread(target=worker, args=(label, seat_list), daemon=True)
            threads.append(t)
            t.start()

        def on_done():
            """Yeh function on_done ka specific kaam handle karta hai."""
            for t in threads: t.join()
            self.running = False
            self._log("--- Race Complete --- Rejections show critical section working", "info")

        threading.Thread(target=on_done, daemon=True).start()

    # --- Reset ---
    def _reset(self):
        """Yeh function seat locking demo ka state reset karta hai."""
        if self.running:
            messagebox.showinfo("Wait", "Race in progress, wait for it to finish.", parent=self.root); return
        # Re-create all locks (safe since no race running)
        self.seat_locks  = {i: threading.Lock() for i in range(1, self.SEATS + 1)}
        self.seat_status = {i: "Free" for i in range(1, self.SEATS + 1)}
        self.seat_owner  = {i: "" for i in range(1, self.SEATS + 1)}
        self._refresh_grid()
        self.log_box.configure(state=tk.NORMAL)
        self.log_box.delete("1.0", tk.END)
        self.log_box.configure(state=tk.DISABLED)
        self._log("All seats reset to Free.", "info")


# =============================================
# MAIN APPLICATION
# =============================================

class CineFlowApp:
    def __init__(self, root):
        """Yeh constructor class ka initial setup karta hai."""
        self.root = root
        self.root.title("Step 4 - Parallel Servers + Load Balancing")
        self.root.geometry("1020x700")
        self.root.configure(bg="#101827")

        self.movies = ["Inception", "The Dark Knight", "Interstellar",
                       "The Matrix", "Avengers: Endgame", "Titanic"]

        # Step 2 ka main object
        self.priority_queue = PriorityQueue()

        self.arrival_counter = 0
        self.next_request_id = 1
        self.processed_requests = []   # processed requests ki list

        # Step 3: Round Robin time quantum
        self.time_quantum = 2

        # Step 4: Multi-Server Parallel Processing
        self.servers = [BookingServer(i + 1) for i in range(3)]
        self.system_lock = threading.Lock()
        self.simulation_running = False
        self.server_threads = []
        self.run_generation = 0
        self.in_progress = []   # jo requests is waqt processing mein hoti hain

        self._setup_styles()
        self._build_ui()

    # ------------------------------------------
    # Styling
    # ------------------------------------------

    def _setup_styles(self):
        """Yeh function _setup_styles ka specific kaam handle karta hai."""
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview",
                        background="#172033", foreground="white",
                        fieldbackground="#172033", rowheight=30,
                        font=("Calibri", 11))
        style.configure("Treeview.Heading",
                        background="#6d28d9", foreground="white",
                        font=("Calibri", 11, "bold"))
        style.map("Treeview", background=[("selected", "#7c3aed")])

    # ------------------------------------------
    # UI Layout
    # ------------------------------------------

    def _build_ui(self):
        """Yeh function _build_ui ka specific kaam handle karta hai."""
        # ---- Title ----
        tk.Label(self.root, text="CineFlow Ticket System",
                 font=("Calibri", 22, "bold"), fg="#c4b5fd", bg="#101827"
                 ).pack(pady=(14, 2))

        tk.Label(self.root,
                 text="Step 2+3: Priority Queue + Round Robin - VIP first, then fair time slicing",
                 font=("Calibri", 11), fg="#9ca3af", bg="#101827"
                 ).pack(pady=(0, 10))

        # ---- Main content: form (left) + queue table (right) ----
        content = tk.Frame(self.root, bg="#101827")
        content.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)

        self._build_form(content)
        self._build_queue_panel(content)

    def _build_form(self, parent):
        """Yeh function _build_form ka specific kaam handle karta hai."""
        # Left form: make it scrollable (canvas + inner frame)
        form_outer = tk.Frame(parent, bg="#172033", width=270)
        form_outer.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 12), pady=5)
        form_outer.pack_propagate(False)

        form_canvas = tk.Canvas(form_outer, bg="#172033", highlightthickness=0)
        form_scroll = ttk.Scrollbar(form_outer, orient="vertical", command=form_canvas.yview)
        form_frame = tk.Frame(form_canvas, bg="#172033")

        form_frame.bind("<Configure>", lambda e: form_canvas.configure(scrollregion=form_canvas.bbox("all")))
        form_canvas.create_window((0, 0), window=form_frame, anchor="nw")
        form_canvas.configure(yscrollcommand=form_scroll.set)

        form_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        form_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        form_canvas.configure(yscrollincrement=24)

        tk.Label(form_frame, text="Add Booking Request",
             font=("Calibri", 14, "bold"), bg="#172033", fg="#c4b5fd"
             ).pack(pady=(14, 10))

        def lbl(text):
            """Yeh function lbl ka specific kaam handle karta hai."""
            tk.Label(form_frame, text=text, bg="#172033", fg="#e5e7eb",
                     font=("Calibri", 10, "bold")).pack(anchor="w", padx=14, pady=(8, 2))

        lbl("Customer Name:")
        self.name_entry = tk.Entry(form_frame, font=("Calibri", 11), bg="#1f2a44", fg="white",
                                   insertbackground="white", relief="flat")
        self.name_entry.pack(fill=tk.X, padx=14)

        lbl("User Type:")
        self.user_type_var = tk.StringVar(value="Normal")
        ttk.Combobox(form_frame, textvariable=self.user_type_var,
                     values=["VIP", "Normal"], state="readonly",
                     font=("Calibri", 11)).pack(fill=tk.X, padx=14)

        lbl("Movie:")
        self.movie_var = tk.StringVar(value=self.movies[0])
        ttk.Combobox(form_frame, textvariable=self.movie_var,
                     values=self.movies, state="readonly",
                     font=("Calibri", 11)).pack(fill=tk.X, padx=14)

        lbl("Seat Number (1-50):")
        self.seat_spin = tk.Spinbox(form_frame, from_=1, to=50,
                                    font=("Calibri", 11), bg="#1f2a44", fg="white",
                                    buttonbackground="#6d28d9", relief="flat")
        self.seat_spin.pack(fill=tk.X, padx=14)

        # Step 3: Burst Time
        lbl("Burst Time (CPU units 1-10):")
        self.burst_spin = tk.Spinbox(form_frame, from_=1, to=10,
                                     font=("Calibri", 11), bg="#1f2a44", fg="white",
                                     buttonbackground="#6d28d9", relief="flat", width=5)
        self.burst_spin.delete(0, tk.END)
        self.burst_spin.insert(0, "4")
        self.burst_spin.pack(fill=tk.X, padx=14)

        tk.Button(form_frame, text="Add to Priority Queue",
                  bg="#7c3aed", fg="white", font=("Calibri", 11, "bold"),
                  padx=10, pady=8, relief="flat", cursor="hand2",
                  command=self._add_request
                  ).pack(fill=tk.X, padx=14, pady=(12, 6))

        bulk_frame = tk.LabelFrame(form_frame, text="Bulk Random Records",
                                   bg="#172033", fg="#facc15",
                                   font=("Calibri", 9, "bold"))
        bulk_frame.pack(fill=tk.X, padx=14, pady=(0, 6))

        self.bulk_count_spin = tk.Spinbox(bulk_frame, from_=1, to=50,
                                          font=("Calibri", 11),
                                          bg="#1f2a44", fg="white",
                                          buttonbackground="#6d28d9",
                                          relief="flat", width=5)
        self.bulk_count_spin.delete(0, tk.END)
        self.bulk_count_spin.insert(0, "5")
        self.bulk_count_spin.pack(side=tk.LEFT, padx=8, pady=5)

        tk.Button(bulk_frame, text="Generate",
                  bg="#2563eb", fg="white", font=("Calibri", 10, "bold"),
                  relief="flat", cursor="hand2",
                  command=self._add_random_requests
                  ).pack(side=tk.LEFT, padx=4, pady=5)

        self.queue_size_label = tk.Label(
            form_frame, text="Queue Size: 0",
            font=("Calibri", 11, "bold"), bg="#172033", fg="#facc15"
        )
        self.queue_size_label.pack(pady=6)

        # Step 3: Parallel Server controls
        tk.Frame(form_frame, bg="#374151", height=1).pack(fill=tk.X, padx=14, pady=(4, 6))
        tk.Label(form_frame, text="Step 3 - Parallel Servers",
                 font=("Calibri", 9, "bold"), bg="#172033", fg="#fbbf24"
                 ).pack(anchor="w", padx=14)

        tk.Button(form_frame, text="Dispatch + Start Servers",
                  bg="#0891b2", fg="white", font=("Calibri", 10, "bold"),
                  padx=10, pady=7, relief="flat", cursor="hand2",
                  command=self._start_servers
                  ).pack(fill=tk.X, padx=14, pady=(4, 2))

        tk.Button(form_frame, text="Stop Servers",
                  bg="#dc2626", fg="white", font=("Calibri", 10, "bold"),
                  padx=10, pady=7, relief="flat", cursor="hand2",
                  command=self._stop_servers
                  ).pack(fill=tk.X, padx=14, pady=(0, 6))

        # Time Quantum - servers internally RR isi value se chalate hain
        tk.Button(form_frame, text="Reset Parallel Processing",
                  bg="#9333ea", fg="white", font=("Calibri", 10, "bold"),
                  padx=10, pady=7, relief="flat", cursor="hand2",
                  command=self._reset_parallel_processing
                  ).pack(fill=tk.X, padx=14, pady=(0, 6))

        q_frame = tk.LabelFrame(form_frame, text="Time Quantum  (server RR slice)",
                                bg="#172033", fg="#facc15",
                                font=("Calibri", 9, "bold"))
        q_frame.pack(fill=tk.X, padx=14, pady=(2, 6))

        self.quantum_spin = tk.Spinbox(q_frame, from_=1, to=10,
                                       font=("Calibri", 11), bg="#1f2a44", fg="white",
                                       buttonbackground="#6d28d9", relief="flat", width=5)
        self.quantum_spin.delete(0, tk.END)
        self.quantum_spin.insert(0, str(self.time_quantum))
        self.quantum_spin.pack(side=tk.LEFT, padx=8, pady=5)

        tk.Button(q_frame, text="Apply", bg="#4f46e5", fg="white",
                  font=("Calibri", 10, "bold"), relief="flat", cursor="hand2",
                  command=self._apply_quantum
                  ).pack(side=tk.LEFT, padx=4, pady=5)

        self.quantum_label = tk.Label(q_frame, text=f"Q={self.time_quantum}",
                                      bg="#172033", fg="#facc15",
                                      font=("Calibri", 10, "bold"))
        self.quantum_label.pack(side=tk.LEFT, padx=4)

        tk.Label(form_frame,
                 text="Priority: VIP=1, Normal=2\nRound Robin: equal time\nslices per request\nParallel: 3 servers run\nsimultaneously",
                 justify="left", bg="#172033", fg="#6ee7b7",
                 font=("Calibri", 9)).pack(padx=14, pady=4, anchor="w")

        # mouse-wheel binding for the form canvas (only when hovered)
        def _form_wheel(event):
            form_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        form_outer.bind("<Enter>", lambda _e: form_canvas.bind_all("<MouseWheel>", _form_wheel))
        form_outer.bind("<Leave>", lambda _e: form_canvas.unbind_all("<MouseWheel>"))

    def _build_queue_panel(self, parent):
        """Yeh function _build_queue_panel ka specific kaam handle karta hai."""
        # Right queue panel: make it scrollable (canvas + inner frame)
        right_outer = tk.Frame(parent, bg="#101827")
        right_outer.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        right_canvas = tk.Canvas(right_outer, bg="#101827", highlightthickness=0)
        right_scroll = ttk.Scrollbar(right_outer, orient="vertical", command=right_canvas.yview)
        right = tk.Frame(right_canvas, bg="#101827")

        right.bind("<Configure>", lambda e: right_canvas.configure(scrollregion=right_canvas.bbox("all")))
        right_canvas.create_window((0, 0), window=right, anchor="nw")
        right_canvas.configure(yscrollcommand=right_scroll.set)

        right_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        right_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        right_canvas.configure(yscrollincrement=24)

        # ---- Waiting Queue table ----
        tk.Label(right, text="Priority Queue  (sorted: VIP first, then FCFS)",
                 font=("Calibri", 12, "bold"), fg="#c4b5fd", bg="#101827"
                 ).pack(anchor="w", pady=(4, 4))

        cols = ("ID", "Name", "User Type", "Priority", "Movie", "Seat", "Burst", "Remaining", "Status")
        self.queue_tree = ttk.Treeview(right, columns=cols, show="headings", height=8)
        widths = {"ID": 45, "Name": 100, "User Type": 80, "Priority": 65,
                  "Movie": 115, "Seat": 50, "Burst": 55, "Remaining": 80, "Status": 90}
        for col in cols:
            self.queue_tree.heading(col, text=col)
            self.queue_tree.column(col, width=widths[col])

        # Color tags
        self.queue_tree.tag_configure("vip",    background="#3b1f6e", foreground="#e9d5ff")
        self.queue_tree.tag_configure("normal", background="#172033", foreground="white")

        self.queue_tree.pack(fill=tk.X, pady=4)

        # ---- Processed table ----
        tk.Label(right, text="Processed Requests  (already removed from queue)",
                 font=("Calibri", 12, "bold"), fg="#6ee7b7", bg="#101827"
                 ).pack(anchor="w", pady=(12, 4))

        cols2 = ("ID", "Name", "User Type", "Priority", "Movie", "Seat", "Burst", "Status")
        self.processed_tree = ttk.Treeview(right, columns=cols2, show="headings", height=6)
        widths2 = {"ID": 45, "Name": 100, "User Type": 80, "Priority": 65,
                   "Movie": 115, "Seat": 50, "Burst": 55, "Status": 90}
        for col in cols2:
            self.processed_tree.heading(col, text=col)
            self.processed_tree.column(col, width=widths2[col])

        self.processed_tree.tag_configure("done", background="#14532d", foreground="#bbf7d0")
        self.processed_tree.pack(fill=tk.X, pady=4)

        # Step 4: Server Status table
        tk.Label(right, text="Server Status  (Step 3: Parallel Processing + Load Balancing)",
                 font=("Calibri", 12, "bold"), fg="#fbbf24", bg="#101827"
                 ).pack(anchor="w", pady=(12, 4))

        cols3 = ("Server", "Queue Size", "Assigned Requests", "Completed")
        self.server_tree = ttk.Treeview(right, columns=cols3, show="headings", height=4)
        widths3 = {"Server": 80, "Queue Size": 90, "Assigned Requests": 280, "Completed": 90}
        for col in cols3:
            self.server_tree.heading(col, text=col)
            self.server_tree.column(col, width=widths3[col])

        self.server_tree.tag_configure("active", background="#1e3a5f", foreground="#bfdbfe")
        self.server_tree.tag_configure("idle",   background="#172033", foreground="#6b7280")
        self.server_tree.pack(fill=tk.X, pady=4)

        # mouse-wheel binding for right panel canvas (only when hovered)
        def _right_wheel(event):
            right_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        right_outer.bind("<Enter>", lambda _e: right_canvas.bind_all("<MouseWheel>", _right_wheel))
        right_outer.bind("<Leave>", lambda _e: right_canvas.unbind_all("<MouseWheel>"))

    # ------------------------------------------
    # Logic
    # ------------------------------------------

    def _is_seat_taken(self, seat_no: int) -> str | None:
        """
        Check karo kya yeh seat already kisi ko assign hai.
        Ab server queues bhi check hoti hain (Step 4).
        """
        for r in self.priority_queue.all_requests():
            if r.seat_no == seat_no:
                return r.name

        for server in self.servers:               # Step 4: server queues bhi check
            for r in server.queue:
                if r.seat_no == seat_no:
                    return r.name

        for r in self.in_progress:                # BUG FIX: popleft ke baad sleep tak
            if r.seat_no == seat_no:
                return r.name

        for r in self.processed_requests:
            if r.seat_no == seat_no:
                return r.name

        return None

    def _add_request(self):
        """Yeh function _add_request ka specific kaam handle karta hai."""
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showerror("Input Error", "Customer name required.")
            return

        try:
            seat_no = int(self.seat_spin.get().replace(',', ''))
        except ValueError:
            messagebox.showerror("Invalid Seat", "Seat number must be a valid integer between 1 and 50.")
            return
        if not 1 <= seat_no <= 50:
            messagebox.showerror("Invalid Seat", "Seat number must be between 1 and 50.")
            return

        # Duplicate seat check
        owner = self._is_seat_taken(seat_no)
        if owner:
            messagebox.showerror(
                "Seat Already Taken",
                f"Seat {seat_no} is already assigned to '{owner}'.\n"
                f"Please choose a different seat."
            )
            print(f"[REJECTED] {name} tried to book Seat {seat_no} "
                  f"- already taken by {owner}")
            return
        # seat validation block end

        user_type = self.user_type_var.get()
        priority  = 1 if user_type == "VIP" else 2

        self.arrival_counter += 1

        burst_time = int(self.burst_spin.get().replace(',', ''))

        req = BookingRequest(
            priority=priority,
            arrival_order=self.arrival_counter,
            request_id=self.next_request_id,
            name=name,
            user_type=user_type,
            movie=self.movie_var.get(),
            seat_no=seat_no,
            burst_time=burst_time
        )

        self.next_request_id += 1
        self.priority_queue.enqueue(req)   # enqueue karte hi queue sort ho jati hai

        # Console output (samajhne ke liye)
        print(f"[ENQUEUE] #{req.request_id} {req.name} ({req.user_type})"
              f"  sort_index={req.sort_index}")
        print(f"  Queue order now: "
              + " -> ".join(f"#{r.request_id}({r.user_type})"
                            for r in self.priority_queue.all_requests()))
        print()

        self.name_entry.delete(0, tk.END)

        # Auto-dispatch: agar servers already chal rahe hain toh seedha assign karo
        if self.simulation_running:
            with self.system_lock:
                server = self._get_least_busy_server()
                req.status = f"Assigned S{server.server_id}"
                server.queue.append(req)
                self.priority_queue._queue.remove(req)   # pq se nikalo
                print(f"[AUTO-DISPATCH] #{req.request_id} {req.name} -> Server {server.server_id}")

        self._refresh_tables()

    def _free_seats(self):
        """Yeh function available seats ki list return karta hai."""
        return [seat for seat in range(1, 51) if self._is_seat_taken(seat) is None]

    def _enqueue_generated_request(self, name, user_type, movie, seat_no, burst_time):
        """Yeh helper generated request ko queue mein safely enqueue karta hai."""
        priority = 1 if user_type == "VIP" else 2
        self.arrival_counter += 1

        req = BookingRequest(
            priority=priority,
            arrival_order=self.arrival_counter,
            request_id=self.next_request_id,
            name=name,
            user_type=user_type,
            movie=movie,
            seat_no=seat_no,
            burst_time=burst_time
        )

        self.next_request_id += 1
        self.priority_queue.enqueue(req)

        if self.simulation_running:
            with self.system_lock:
                server = self._get_least_busy_server()
                req.status = f"Assigned S{server.server_id}"
                server.queue.append(req)
                self.priority_queue._queue.remove(req)
                print(f"[AUTO-DISPATCH] #{req.request_id} {req.name} -> Server {server.server_id}")

        return req

    def _add_random_requests(self):
        """Yeh function bulk random records generate karta hai."""
        try:
            count = int(self.bulk_count_spin.get().replace(",", ""))
            if count < 1:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid", "Record count must be a positive integer.")
            return

        free_seats = self._free_seats()
        if not free_seats:
            messagebox.showerror("No Free Seats", "All seats are already assigned.")
            return

        if count > len(free_seats):
            messagebox.showerror(
                "Not Enough Seats",
                f"Only {len(free_seats)} free seats are available. "
                f"Please enter {len(free_seats)} or less."
            )
            return

        sample_names = [
            "Ali", "Ayesha", "Hamza", "Sara", "Usman",
            "Hira", "Bilal", "Noor", "Zain", "Maham",
            "Danish", "Iqra", "Taha", "Mina", "Rehan"
        ]
        chosen_seats = random.sample(free_seats, count)
        created = []

        for index, seat_no in enumerate(chosen_seats, start=1):
            user_type = random.choice(["VIP", "Normal"])
            movie = random.choice(self.movies)
            burst_time = random.randint(1, 10)
            base_name = random.choice(sample_names)
            name = f"{base_name}-{self.next_request_id}"

            req = self._enqueue_generated_request(
                name=name,
                user_type=user_type,
                movie=movie,
                seat_no=seat_no,
                burst_time=burst_time
            )
            created.append(req)
            print(f"[BULK {index}/{count}] #{req.request_id} {req.name} "
                  f"({req.user_type}) movie={req.movie} seat={req.seat_no} "
                  f"burst={req.burst_time} sort_index={req.sort_index}")

        print(f"[BULK] Added {len(created)} random records to the priority queue.")
        self._refresh_tables()

    # ------------------------------------------
    # Step 4: Load Balancing + Parallel Servers
    # ------------------------------------------

    def _apply_quantum(self):
        """Yeh function server RR quantum update karta hai."""
        try:
            val = int(self.quantum_spin.get().replace(",", ""))
            if val < 1:
                raise ValueError
            self.time_quantum = val
            self.quantum_label.config(text=f"Q={val}")
            print(f"[QUANTUM] Time quantum -> {val}")
        except ValueError:
            messagebox.showerror("Invalid", "Time quantum must be a positive integer.")

    def _get_least_busy_server(self):
        """
        Load Balancing: sabse choti queue wala server chuno.
        Yeh ensure karta hai koi server overloaded na ho.
        """
        return min(self.servers, key=lambda s: len(s.queue))

    def _dispatch_to_servers(self):
        """
        Step 4 - Load Balancing:
        Priority queue se saari requests nikalo aur
        least busy server ko assign karo.
        Priority order preserve hota hai (VIP pehle dispatch hote hain).
        """
        with self.system_lock:
            while not self.priority_queue.is_empty():
                req = self.priority_queue.dequeue()
                server = self._get_least_busy_server()
                req.status = f"Assigned S{server.server_id}"
                server.queue.append(req)
                print(f"[DISPATCH] #{req.request_id} {req.name} ({req.user_type})"
                      f" -> Server {server.server_id}  (server_queue={len(server.queue)})")

    def _server_worker(self, server, session_id):
        """
        Step 4 - Har server ka thread yeh function run karta hai.
        Step 3 ka Round Robin yahan per-server apply hota hai.

        Flow:
          1. Server apni queue se request uthata hai
          2. min(quantum, remaining) units execute karta hai
          3. remaining > 0  -> re-queue (end of this server's queue)
          4. remaining == 0 -> processed_requests mein add
          5. UI update via root.after (thread-safe)
        """
        while self.simulation_running and session_id == self.run_generation:
            req = None

            with self.system_lock:
                if server.queue:
                    req = server.queue.popleft()
                    req.status = f"Processing S{server.server_id}"
                    self.in_progress.append(req)   # BUG FIX: track during sleep

            if req is None:
                time.sleep(0.3)
                continue

#hr req ko server uske fixed time k acc cpu milta hai
            # RR execution - lock ke bahar taake doosre servers block na hon
            execution = min(self.time_quantum, req.remaining_time)
            time.sleep(execution * 0.4)   # simulated CPU burst

            with self.system_lock:
                if req in self.in_progress:
                    self.in_progress.remove(req)   # BUG FIX: sleep khatam, ab visible hai

#continue matlab:is loop ka ye round skip karo, next iteration par chalay jao”
                if not self.simulation_running or session_id != self.run_generation:
                    continue

# Agar system band ho chuka ho ya reset ho gaya ho (naya session chal raha ho),
# to current process ko skip karke next loop par chale jao.
#“itna kaam ho gaya, ab itna aur bacha hai”
                req.remaining_time -= execution
                server.total_busy += execution

                if req.remaining_time > 0:
                    # Kaam bacha hai - is server ke queue ke end mein wapas bhejo
                    req.status = "Re-queued"
                    self.arrival_counter += 1
                    req.arrival_order = self.arrival_counter
                    req.sort_index = (req.priority, req.arrival_order)
                    server.queue.append(req)
                    print(f"[S{server.server_id}] #{req.request_id} {req.name}"
                          f"  Re-queued | remaining={req.remaining_time}")
                else:
                    # Saara burst use ho gaya - request complete
                    req.status = f"Done S{server.server_id}"
                    self.processed_requests.append(req)
                    server.processed_count += 1
                    print(f"[S{server.server_id}] #{req.request_id} {req.name}"
                          f"  COMPLETED (burst={req.burst_time})")

            # Thread-safe UI update
            self.root.after(0, self._refresh_tables)

    def _start_servers(self):
        """Yeh function parallel servers start karta hai."""
        if self.simulation_running:
            messagebox.showinfo("Already Running", "Servers are already running.")
            return
        if self.priority_queue.is_empty():
            messagebox.showinfo("No Requests", "Add requests to the queue first.")
            return

        self._dispatch_to_servers()          # load balance sabhi waiting requests
        self.simulation_running = True
        self.run_generation += 1
        session_id = self.run_generation
        self.server_threads = []

        for server in self.servers:
            t = threading.Thread(target=self._server_worker,
                                 args=(server, session_id), daemon=True)
            self.server_threads.append(t)
            t.start()

        self._refresh_tables()
        print("[SYSTEM] 3 parallel servers started!")
        messagebox.showinfo("Servers Started",
                            "3 parallel booking servers are now running!\n"
                            "Watch the Server Status table.")

    def _stop_servers(self):
        """Yeh function chalti hui server processing stop karta hai."""
        self.simulation_running = False
        self._refresh_tables()
        print("[SYSTEM] All servers stopped.")
        messagebox.showinfo("Stopped", "All servers have been stopped.")

    def _reset_parallel_processing(self):
        """Yeh function parallel processing data aur counters clear karta hai."""
        self.simulation_running = False
        self.run_generation += 1

        with self.system_lock:
            self.priority_queue._queue.clear()
            self.processed_requests.clear()
            self.in_progress.clear()
            self.arrival_counter = 0
            self.next_request_id = 1

            for server in self.servers:
                server.queue.clear()
                server.processed_count = 0
                server.total_busy = 0

        self.name_entry.delete(0, tk.END)
        self._refresh_tables()
        print("[SYSTEM] Parallel processing reset. Queues, servers, and counters cleared.")
        messagebox.showinfo("Reset", "Parallel processing data has been reset.")

    def _refresh_tables(self):
        """Yeh function tamam tables ko thread-safe tareeqe se refresh karta hai."""
        # Take thread-safe snapshots of shared data
        with self.system_lock:
            queue_snapshot     = self.priority_queue.all_requests()
            processed_snapshot = list(self.processed_requests)
            server_snapshot    = [(s.server_id,
                                   list(s.queue),
                                   s.processed_count) for s in self.servers]

        # Clear all trees
        for item in self.queue_tree.get_children():
            self.queue_tree.delete(item)
        for item in self.processed_tree.get_children():
            self.processed_tree.delete(item)
        for item in self.server_tree.get_children():
            self.server_tree.delete(item)

        # Priority Queue
        for r in queue_snapshot:
            tag = "vip" if r.user_type == "VIP" else "normal"
            self.queue_tree.insert("", tk.END, tags=(tag,), values=(
                r.request_id, r.name, r.user_type,
                r.priority, r.movie, r.seat_no,
                r.burst_time, r.remaining_time, r.status
            ))

        # Processed
        for r in processed_snapshot:
            self.processed_tree.insert("", tk.END, tags=("done",), values=(
                r.request_id, r.name, r.user_type,
                r.priority, r.movie, r.seat_no, r.burst_time, r.status
            ))

        # Server Status table (Step 4)
        for sid, q, done in server_snapshot:
            if q:
                assigned = ", ".join(f"{r.request_id}: {r.name} [{r.user_type}]" for r in q)
            else:
                assigned = "Idle"
            tag = "active" if q else "idle"
            self.server_tree.insert("", tk.END, tags=(tag,), values=(
                f"Server {sid}", len(q), assigned, done
            ))

        # Queue size badge
        self.queue_size_label.config(text=f"Queue Size: {self.priority_queue.size()}")
        self.root.update_idletasks()


# =============================================
# MAIN MENU
# =============================================

class MainMenu:
    """
    Landing page - choose which OS concept to explore.
    Har concept apni alag focused window mein khulta hai.
    """
    def __init__(self, root):
        """Yeh constructor class ka initial setup karta hai."""
        self.root = root
        self.root.title("CineFlow OS Simulation - Menu")
        self.root.geometry("700x500")
        self.root.configure(bg=BG)
        self.root.resizable(False, False)
        _apply_style()
        self._build()

    def _build(self):
        """Yeh function UI layout aur controls banata hai."""
        tk.Label(self.root, text="CineFlow OS Simulation",
                 font=("Calibri", 26, "bold"), fg=PURPLL, bg=BG).pack(pady=(28, 4))
        tk.Label(self.root, text="Select an OS Concept to explore - each opens in its own window",
                 font=("Calibri", 11), fg=GRAY, bg=BG).pack(pady=(0, 26))

        grid = tk.Frame(self.root, bg=BG)
        grid.pack()

        concepts = [
            ("Step 1", "Priority Queue",
             "VIP users processed\nbefore Normal users",
             PURPLE, self._pq),
            ("Step 2", "Round Robin",
             "Fair CPU time slices\nwith time quantum",
             GREEN, self._rr),
            ("Step 3", "Parallel Servers",
             "3 servers run simultaneously\nLoad balancing + Synchronization",
             CYAN, self._ps),
            ("Step 4", "Seat Locking",
             "Critical section prevents\nduplicate seat bookings",
             "#9333ea", self._sl),
        ]

        for i, (step, title, desc, color, cmd) in enumerate(concepts):
            card = tk.Frame(grid, bg=PANEL, width=290, height=158, relief="flat")
            card.grid(row=i // 2, column=i % 2, padx=14, pady=10)
            card.pack_propagate(False)
            tk.Label(card, text=step, font=("Calibri", 9, "bold"),
                     bg=PANEL, fg=GRAY).pack(anchor="w", padx=14, pady=(12, 0))
            tk.Label(card, text=title, font=("Calibri", 16, "bold"),
                     bg=PANEL, fg=color).pack(anchor="w", padx=14)
            tk.Label(card, text=desc, font=("Calibri", 10),
                     bg=PANEL, fg="#e5e7eb", justify="left").pack(anchor="w", padx=14, pady=4)
            tk.Button(card, text=f"Open  {title}", command=cmd,
                      bg=color, fg="white", font=("Calibri", 10, "bold"),
                      relief="flat", cursor="hand2", padx=8, pady=4
                      ).pack(anchor="w", padx=14)

    def _pq(self):
        """Priority Queue wali window kholta hai."""
        PriorityQueueWindow(tk.Toplevel(self.root))

    def _rr(self):
        """Round Robin wali window kholta hai."""
        RoundRobinWindow(tk.Toplevel(self.root))

    def _ps(self):
        """Parallel Servers wali window kholta hai."""
        CineFlowApp(tk.Toplevel(self.root))

    def _sl(self):
        """Seat Locking wali window kholta hai."""
        SeatLockingWindow(tk.Toplevel(self.root))


# =============================================
# RUN
# =============================================

if __name__ == "__main__":
    root = tk.Tk()
    MainMenu(root)
    root.mainloop()
