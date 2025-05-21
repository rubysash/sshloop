# main.py
"""
Main GUI for the SSH Host Logger tool.
Layout: Hosts tree (left), command dropdown + preview + output display (right).
"""
from concurrent.futures import ThreadPoolExecutor 
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from ttkbootstrap import Style

import os
import threading
import queue

from config import MAX_THREADS, COMMANDS_DIR, BLACKLISTED_COMMAND_WORDS, VERSION

from file_handler import load_csv, load_json_commands, save_results
from ssh_worker import run_ssh_task

class HostLoggerApp:

    def __init__(self, root):
        self.root = root
        self.queue = queue.Queue()
        self.hosts = []
        self.commands = {}

        self.selected_command_key = None
        self.tree_items = {}  # maps item IDs to host indices

        self.setup_ui()
        self.username_entry.insert(0, "root")
        self.load_commands(COMMANDS_DIR)

        self.cached_password = None  # cache session password possibility
        self.save_password_session = tk.BooleanVar(value=False)  # Tracks checkbox state


    def setup_ui(self):
        """Build all GUI widgets and layout."""
        self.root.title(f"SSH Looper v {VERSION}")
        self.root.geometry("900x600")

        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill="both", expand=True)

        # LEFT FRAME
        self.left_frame = ttk.Frame(self.main_frame, width=450)
        self.left_frame.pack(side="left", fill="both", expand=True)

        ## Treeview Button to Load
        self.load_button = ttk.Button(self.left_frame, text="Load Hosts CSV", command=self.browse_csv)
        self.load_button.pack(fill="x", pady=(5, 5))

        ## Treeview
        self.tree = ttk.Treeview(self.left_frame, columns=("IP", "Port", "Status"), show="headings")
        self.tree.heading("IP", text="IP", anchor="w")
        self.tree.heading("Port", text="Port", anchor="w")
        self.tree.heading("Status", text="Status", anchor="w")
        self.tree.column("IP", anchor="w")
        self.tree.column("Port", anchor="w")
        self.tree.column("Status", anchor="w")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.display_output)

        ## Description Field 
        self.description_label = ttk.Label(self.left_frame, text="Command Description:")
        self.description_label.pack(fill="x", pady=(5, 0))
        self.command_description = tk.Text(self.left_frame, height=5, wrap="word", state="disabled")
        self.command_description.pack(fill="x", padx=5, pady=(0, 5))

        # RIGHT FRAME
        self.right_frame = ttk.Frame(self.main_frame, width=450)
        self.right_frame.pack(side="right", fill="both", expand=True, padx=10)

        ## Same Username for all
        self.username_label = ttk.Label(self.right_frame, text="SSH Username:")
        self.username_label.pack(fill="x")
        self.username_entry = ttk.Entry(self.right_frame)
        self.username_entry.pack(fill="x", pady=(0, 5))

        ## Filter
        self.command_label = ttk.Label(self.right_frame, text="Filter Commands by Keyword:")
        self.command_label.pack(fill="x", pady=(0, 2))
        self.command_entry = ttk.Entry(self.right_frame)
        self.command_entry.pack(fill="x", pady=(0, 5))
        self.command_entry.bind("<KeyRelease>", self.filter_commands)

        ## Filtered ListBox
        self.command_listbox = tk.Listbox(self.right_frame, height=5)
        self.command_listbox.pack(fill="x", pady=(0, 5))
        self.command_listbox.bind("<<ListboxSelect>>", self.select_command_from_list)

        ## Sample Command from Json
        self.command_preview_label = ttk.Label(self.right_frame, text="Command to Be Run:")
        self.command_preview_label.pack(fill="x", pady=(0, 2))
        self.command_preview = tk.Text(self.right_frame, height=3, state="disabled", wrap="word")
        self.command_preview.pack(fill="x", pady=(0, 5))

        ## Manual Command Input
        self.manual_command_label = ttk.Label(self.right_frame, text="Manual Command (Overrides Selection):")
        self.manual_command_label.pack(fill="x", pady=(0, 2))
        self.manual_command_entry = ttk.Entry(self.right_frame)
        self.manual_command_entry.pack(fill="x", pady=(0, 5))

        # Frame in Right Side for Output
        output_frame = ttk.Frame(self.right_frame)
        output_frame.pack(fill="both", expand=False, pady=(0, 5))

        self.output_display_label = ttk.Label(output_frame, text="Result of Command:")
        self.output_display_label.pack(fill="x", pady=(0, 2))
        self.output_display = tk.Text(output_frame, wrap="word", height=10, state="disabled")
        self.output_display.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(output_frame, command=self.output_display.yview)
        scrollbar.pack(side="right", fill="y")
        self.output_display.config(yscrollcommand=scrollbar.set)

        # Buttons
        button_frame = ttk.Frame(self.right_frame)
        button_frame.pack(fill="x", pady=(0, 5))

        self.go_button = ttk.Button(button_frame, text="Run Command", command=self.ask_password_then_execute)
        self.go_button.pack(side="left", expand=True, fill="x", padx=(0, 5))

        self.export_button = ttk.Button(button_frame, text="Export", command=self.export_results)
        self.export_button.pack(side="left", expand=True, fill="x")


    def filter_commands(self, event=None):
        typed = self.command_entry.get().lower()
        self.command_listbox.delete(0, tk.END)

        for key in sorted(self.commands.keys()):
            command = self.commands[key].get("command", "").lower()
            if typed in key.lower() or typed in command:
                self.command_listbox.insert(tk.END, key)


    def browse_csv(self):
        """Open file dialog to choose and load a CSV file."""
        script_dir = os.path.dirname(os.path.realpath(__file__))
        assets_dir = os.path.join(script_dir, "assets")

        # Ensure assets directory exists
        if not os.path.isdir(assets_dir):
            messagebox.showerror(
                "Missing Folder",
                f"'assets' directory not found at:\n{assets_dir}\nCreating it for you."
            )
            os.makedirs(assets_dir, exist_ok=True)
            return

        # Create default hosts.csv if missing
        default_csv = os.path.join(assets_dir, "hosts.csv")
        if not os.path.exists(default_csv):
            with open(default_csv, "w", newline="") as f:
                f.write("hostname,ip,port\n")
                f.write("SampleServer,192.168.1.100,22\n")

            messagebox.showinfo(
                "Created Default CSV",
                f"'hosts.csv' was missing and has been created at:\n{default_csv}\nYou may edit this file with your actual hosts."
            )
            return

        # Proceed with file dialog
        file_path = filedialog.askopenfilename(
            title="Select Host CSV File",
            filetypes=[("CSV Files", "*.csv")],
            initialdir=assets_dir
        )
        if file_path:
            self.load_hosts(file_path)


    def select_command_from_list(self, event=None):
        if not self.command_listbox.curselection():
            return

        index = self.command_listbox.curselection()[0]
        selected = self.command_listbox.get(index)
        self.command_entry.delete(0, tk.END)
        self.command_entry.insert(0, selected)
        self.selected_command_key = selected
        self.update_command_preview()


    def load_hosts(self, file_path):
        self.hosts = load_csv(file_path)
        for idx, host in enumerate(self.hosts):
            item_id = self.tree.insert("", "end", values=(host["ip"], host["port"], "Pending"))
            self.tree_items[item_id] = idx


    def load_commands(self, directory_path):
        categorized = load_json_commands(directory_path)
        self.commands = {}  # Flattened command map with full keys

        dropdown_items = []
        for category in sorted(categorized.keys()):
            for label in sorted(categorized[category].keys()):
                full_key = f"{category}: {label}"
                self.commands[full_key] = categorized[category][label]
                dropdown_items.append(full_key)

        # Update Listbox instead of old Combobox
        self.command_listbox.delete(0, tk.END)
        for item in sorted(dropdown_items):
            self.command_listbox.insert(tk.END, item)


    def update_command_preview(self, event=None):
        key = getattr(self, 'selected_command_key', None)
        if not key:
            return

        command_info = self.commands.get(key, {})
        command = command_info.get("command", "")
        description = command_info.get("description", "No description provided.")

        # Update command preview
        self.command_preview.config(state="normal")
        self.command_preview.delete("1.0", tk.END)
        self.command_preview.insert(tk.END, command)
        self.command_preview.config(state="disabled")

        # Update description
        self.command_description.config(state="normal")
        self.command_description.delete("1.0", tk.END)
        self.command_description.insert(tk.END, description)
        self.command_description.config(state="disabled")


    def start_execution(self):
        username = self.username_entry.get()
        password = getattr(self, 'ssh_password', '')

        if not self.hosts:
            messagebox.showerror("No Hosts Loaded", "You must load a hosts CSV file before running a command.")
            return

        if not username or not password:
            messagebox.showerror("Missing Credentials", "Username or password is missing.")
            return

        # Check for manual command
        manual_command = self.manual_command_entry.get().strip()
        command_info = {}

        if manual_command:
            confirm = messagebox.askyesno(
                "Manual Command Confirmation",
                "You are about to run a manual command on all hosts. Are you sure?"
            )
            if not confirm:
                return

            # Blacklist check
            lowered_cmd = manual_command.lower()
            if any(bad_word in lowered_cmd for bad_word in BLACKLISTED_COMMAND_WORDS):
                messagebox.showerror("Blocked Command", f"The command contains a restricted word. Execution denied.")
                return

            command_info = {
                "command": manual_command,
                "parse": "(.+)"  # generic fallback regex
            }
        else:
            command_info = self.commands.get(self.selected_command_key)
            if not command_info:
                messagebox.showerror("Command Error", "No command selected.")
                return

        for host in self.hosts:
            host.update({
                "username": username,
                "password": password,
            })

        with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
            for host in self.hosts:
                executor.submit(run_ssh_task, host, command_info, self.queue)

        self.root.after(100, self.poll_queue)


    def export_results(self):
        """Export current SSH results to an XLSX file."""
        if not self.hosts:
            messagebox.showwarning("No Data", "No host data available to export.")
            return

        filetypes = [("Excel files", "*.xlsx")]
        default_filename = f"results_{self._get_timestamp_for_filename()}.xlsx"
        filepath = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=filetypes,
            initialfile=default_filename
        )

        if not filepath:
            return  # User canceled

        try:
            save_results(self.hosts, filepath)
            messagebox.showinfo("Export Successful", f"Results saved to:\n{filepath}")
            os.startfile(filepath)
        except Exception as e:
            messagebox.showerror("Export Failed", str(e))


    def _get_timestamp_for_filename(self):
        """Utility to create timestamp string for filenames."""
        from datetime import datetime
        return datetime.now().strftime("%Y%m%d_%H%M%S")


    def poll_queue(self):
        try:
            while True:
                result = self.queue.get_nowait()
                self.update_tree(result)
        except queue.Empty:
            self.root.after(100, self.poll_queue)


    def ask_password_then_execute(self):
        if not self.hosts:
            messagebox.showerror("No Hosts Loaded", "You must load a hosts CSV file before running a command.")
            return

        if self.cached_password and self.save_password_session.get():
            self.ssh_password = self.cached_password
            self.start_execution()
            return

        password_popup = tk.Toplevel(self.root)
        password_popup.title("Enter SSH Password")
        password_popup.geometry("300x150")
        password_popup.grab_set()

        label = ttk.Label(password_popup, text="SSH Password:")
        label.pack(pady=(10, 5))

        password_entry = ttk.Entry(password_popup, show="*")
        password_entry.pack(fill="x", padx=10)
        password_entry.focus_set()

        save_checkbox = ttk.Checkbutton(
            password_popup,
            text="Save During Session",
            variable=self.save_password_session
        )
        save_checkbox.pack(pady=5)

        def on_submit(event=None):
            self.ssh_password = password_entry.get()
            if self.save_password_session.get():
                self.cached_password = self.ssh_password
            password_popup.destroy()
            self.start_execution()

        submit_btn = ttk.Button(password_popup, text="Submit", command=on_submit)
        submit_btn.pack(pady=10)

        password_entry.bind("<Return>", on_submit)


    def update_tree(self, result):
        for item_id, idx in self.tree_items.items():
            if self.hosts[idx]["ip"] == result["ip"]:
                self.hosts[idx].update(result)
                if result["error"]:
                    status = "Error"
                else:
                    status = "Complete"
                self.tree.set(item_id, "Status", status)
                break


    def display_output(self, event):
        selected = self.tree.focus()
        if selected:
            idx = self.tree_items[selected]
            output = self.hosts[idx].get("output", "")
            error = self.hosts[idx].get("error", "")
            display_text = f"Output:\n{output}\n\nError:\n{error}" if error else f"Output:\n{output}"

            self.output_display.config(state="normal")
            self.output_display.delete("1.0", tk.END)
            self.output_display.insert(tk.END, display_text)
            self.output_display.config(state="disabled")


if __name__ == "__main__":
    root = tk.Tk()
    Style("darkly")
    app = HostLoggerApp(root)
    root.mainloop()
