#!/usr/bin/env python3
# Modern Tkinter GUI for PDF OCR processor on Windows
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import os
import json
from pathlib import Path
from run_process_0100 import process_pdf

class ModernApp:
    def __init__(self, root):
        self.root = root
        self.setup_window()
        self.setup_variables()
        self.setup_styles()
        self.create_widgets()
        self.load_settings()
        
    def setup_window(self):
        """Настройка основного окна"""
        self.root.title('PDF2Searchable v3.0 by Aleksei Sokolov')
        self.root.geometry('800x700')
        self.root.minsize(600, 500)
        
        # Центрирование окна
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (800 // 2)
        y = (self.root.winfo_screenheight() // 2) - (700 // 2)
        self.root.geometry(f'800x700+{x}+{y}')
        
        # Иконка (если есть)
        try:
            self.root.iconbitmap('icon.ico')
        except:
            pass
            
    def setup_variables(self):
        """Инициализация переменных"""
        self.input_var = tk.StringVar(value=os.path.join(os.getcwd(), '0100.pdf'))
        self.output_var = tk.StringVar(value=os.path.join(os.getcwd(), '0100_searchable.pdf'))
        self.hide_text_var = tk.BooleanVar(value=False)
        self.visible_hide_var = tk.BooleanVar(value=False)
        self.flip_x_var = tk.BooleanVar(value=True)
        self.flip_y_var = tk.BooleanVar(value=True)
        self.font_size_var = tk.IntVar(value=8)
        self.top_shift_var = tk.IntVar(value=20)
        self.batch_files = []  # список выбранных входных файлов для пакетной обработки
        
        # Путь к настройкам
        self.settings_path = Path(__file__).parent / 'settings.json'
        
    def setup_styles(self):
        """Настройка стилей"""
        self.style = ttk.Style()
        
        # Современная цветовая схема
        self.colors = {
            'primary': '#2E86AB',      # Синий
            'secondary': '#A23B72',    # Розовый
            'success': '#F18F01',      # Оранжевый
            'background': '#F5F5F5',   # Светло-серый
            'surface': '#FFFFFF',      # Белый
            'text': '#333333',         # Темно-серый
            'border': '#CCCCCC'        # Серый
        }
        
        # Настройка стилей ttk
        self.style.configure('Title.TLabel', 
                           font=('Segoe UI', 16, 'bold'),
                           foreground=self.colors['primary'])
        
        self.style.configure('Heading.TLabel',
                           font=('Segoe UI', 11, 'bold'),
                           foreground=self.colors['text'])
        
        self.style.configure('Modern.TButton',
                           font=('Segoe UI', 10, 'bold'),
                           padding=(20, 10))
        
        self.style.configure('Success.TButton',
                           font=('Segoe UI', 10, 'bold'),
                           padding=(20, 10))
        
        # Настройка цветов кнопок
        self.style.map('Modern.TButton',
                      background=[('active', self.colors['primary']),
                                ('pressed', self.colors['secondary'])])
        
        self.style.map('Success.TButton',
                      background=[('active', self.colors['success']),
                                ('pressed', '#D17A00')])
        
    def create_widgets(self):
        """Create interface widgets"""
        # Main container with padding
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Configure stretching
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="PDF2Searchable", style='Title.TLabel')
        title_label.pack(pady=(0, 20))
        
        # File section
        self.create_file_section(main_frame)
        
        # Settings section
        self.create_settings_section(main_frame)
        
        # Options section
        self.create_options_section(main_frame)
        
        # Action buttons
        self.create_action_section(main_frame)
        
        # Log section
        self.create_log_section(main_frame)
        
    def create_file_section(self, parent):
        """Create file selection section"""
        # Section frame
        file_frame = ttk.LabelFrame(parent, text="Files", padding="10")
        file_frame.pack(fill=tk.X, pady=(0, 10))
        file_frame.columnconfigure(1, weight=1)
        
        # Input file
        ttk.Label(file_frame, text="Input PDF:").grid(row=0, column=0, sticky='e', padx=(0, 10))
        self.input_entry = ttk.Entry(file_frame, textvariable=self.input_var)
        self.input_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        ttk.Button(file_frame, text="Browse", command=self.browse_input).grid(row=0, column=2)

        # Multi-input selection
        ttk.Button(file_frame, text="Browse Multiple", command=self.browse_inputs_multiple).grid(row=1, column=2, pady=(5, 0))
        self.batch_status_var = tk.StringVar(value="Batch: 0 files selected")
        ttk.Label(file_frame, textvariable=self.batch_status_var).grid(row=1, column=1, sticky='w', padx=(0, 10), pady=(5, 0))
        
        # Output file
        ttk.Label(file_frame, text="Output PDF:").grid(row=2, column=0, sticky='e', padx=(0, 10), pady=(5, 0))
        self.output_entry = ttk.Entry(file_frame, textvariable=self.output_var)
        self.output_entry.grid(row=2, column=1, sticky=(tk.W, tk.E), padx=(0, 10), pady=(5, 0))
        ttk.Button(file_frame, text="Browse", command=self.browse_output).grid(row=2, column=2, pady=(5, 0))
        
    def create_settings_section(self, parent):
        """Create settings section"""
        # Section frame
        settings_frame = ttk.LabelFrame(parent, text="Settings", padding="10")
        settings_frame.pack(fill=tk.X, pady=(0, 10))
        settings_frame.columnconfigure(1, weight=1)
        settings_frame.columnconfigure(3, weight=1)
        
        # Font size
        ttk.Label(settings_frame, text="Font size:").grid(row=0, column=0, sticky='e', padx=(0, 10))
        self.font_spin = ttk.Spinbox(settings_frame, from_=4, to=48, textvariable=self.font_size_var, 
                                   width=10, command=self.save_settings)
        self.font_spin.grid(row=0, column=1, sticky='w', padx=(0, 20))
        
        # Top shift
        ttk.Label(settings_frame, text="Top shift (px):").grid(row=0, column=2, sticky='e', padx=(0, 10))
        ttk.Entry(settings_frame, textvariable=self.top_shift_var, width=10).grid(row=0, column=3, sticky='w')
        
    def create_options_section(self, parent):
        """Create options section"""
        # Section frame
        options_frame = ttk.LabelFrame(parent, text="Processing Options", padding="10")
        options_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Hide text checkbox
        self.hide_text_cb = ttk.Checkbutton(options_frame, text="Hide text (image covers text)", 
                                          variable=self.hide_text_var, command=self.update_output_filename)
        self.hide_text_cb.pack(anchor='w', pady=2)
        
        # Visible&Hide checkbox
        self.visible_hide_cb = ttk.Checkbutton(options_frame, text="Visible&Hide (create both versions)", 
                                            variable=self.visible_hide_var, command=self.update_output_filename)
        self.visible_hide_cb.pack(anchor='w', pady=2)
        
    def create_action_section(self, parent):
        """Create action buttons section"""
        action_frame = ttk.Frame(parent)
        action_frame.pack(pady=10)
        
        self.run_btn = ttk.Button(action_frame, text="🚀 Start Processing", 
                                 command=self.on_run, style='Success.TButton')
        self.run_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.clear_btn = ttk.Button(action_frame, text="🗑️ Clear Log", 
                                  command=self.clear_log, style='Modern.TButton')
        self.clear_btn.pack(side=tk.LEFT)
        
    def create_log_section(self, parent):
        """Create log section"""
        # Section frame
        log_frame = ttk.LabelFrame(parent, text="Processing Log", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        # Text widget with scrollbar
        self.log = tk.Text(log_frame, width=80, height=15, wrap=tk.WORD,
                          font=('Consolas', 9), bg='#F8F8F8', fg='#333333')
        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log.yview)
        self.log.configure(yscrollcommand=scrollbar.set)
        
        self.log.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
    def browse_input(self):
        """Select input file"""
        file_path = filedialog.askopenfilename(
            title="Select Input PDF File",
            filetypes=[('PDF files', '*.pdf'), ('All files', '*.*')]
        )
        if file_path:
            self.input_var.set(file_path)
            # Auto-suggest output filename
            if not self.output_var.get() or '0100_searchable.pdf' in self.output_var.get():
                base_name = os.path.splitext(file_path)[0]
                suffix = "_searchable"
                if self.hide_text_var.get():
                    suffix += "_Hide"
                self.output_var.set(f"{base_name}{suffix}.pdf")
    
    def browse_output(self):
        """Select output file"""
        file_path = filedialog.asksaveasfilename(
            title="Save As",
            defaultextension='.pdf',
            filetypes=[('PDF files', '*.pdf'), ('All files', '*.*')]
        )
        if file_path:
            self.output_var.set(file_path)
    
    def browse_inputs_multiple(self):
        """Select multiple input files for batch processing"""
        files = filedialog.askopenfilenames(
            title="Select Input PDF Files",
            filetypes=[('PDF files', '*.pdf'), ('All files', '*.*')]
        )
        if files:
            self.batch_files = list(files)
            self.batch_status_var.set(f"Batch: {len(self.batch_files)} files selected")
            # Also reflect first file to input entry for convenience and output name update
            self.input_var.set(self.batch_files[0])
            self.update_output_filename()
    
    def save_settings(self):
        """Save settings"""
        try:
            data = {
                'font_size': int(self.font_size_var.get()),
                'top_shift': int(self.top_shift_var.get()),
                'hide_text': self.hide_text_var.get(),
                'visible_hide': self.visible_hide_var.get(),
                'flip_x': self.flip_x_var.get(),
                'flip_y': self.flip_y_var.get()
            }
            with open(self.settings_path, 'w', encoding='utf-8') as fh:
                json.dump(data, fh, ensure_ascii=False, indent=2)
        except Exception as e:
            self.log_message(f"Error saving settings: {e}")
    
    def load_settings(self):
        """Load settings"""
        try:
            if self.settings_path.exists():
                with open(self.settings_path, 'r', encoding='utf-8') as fh:
                    data = json.load(fh)
                    self.font_size_var.set(int(data.get('font_size', 8)))
                    self.top_shift_var.set(int(data.get('top_shift', 20)))
                    self.hide_text_var.set(data.get('hide_text', False))
                    self.visible_hide_var.set(data.get('visible_hide', False))
                    self.flip_x_var.set(data.get('flip_x', True))
                    self.flip_y_var.set(data.get('flip_y', True))
        except Exception as e:
            self.log_message(f"Error loading settings: {e}")
    
    def log_message(self, message):
        """Add message to log"""
        self.log.insert(tk.END, f"{message}\n")
        self.log.see(tk.END)
        self.root.update_idletasks()
    
    def clear_log(self):
        """Clear log"""
        self.log.delete(1.0, tk.END)
    
    def update_output_filename(self):
        """Update output filename based on options"""
        input_file = self.input_var.get()
        if input_file and os.path.exists(input_file):
            base_name = os.path.splitext(input_file)[0]
            suffix = "_searchable"
            if self.hide_text_var.get():
                suffix += "_Hide"
            self.output_var.set(f"{base_name}{suffix}.pdf")
    
    
    
    def on_run(self):
        """Start processing"""
        # Input validation
        input_file = self.input_var.get()
        output_file = self.output_var.get()
        
        if (not input_file or not os.path.exists(input_file)) and not self.batch_files:
            messagebox.showerror("Error", "Please select an existing input PDF file or choose multiple files")
            return
        
        if not output_file and not self.batch_files:
            messagebox.showerror("Error", "Please specify output file path")
            return
        
        # Get parameters
        hide_text = self.hide_text_var.get()
        visible_hide = self.visible_hide_var.get()
        flip_x = self.flip_x_var.get()
        flip_y = self.flip_y_var.get()
        font_size = int(self.font_size_var.get())
        top_shift_px = float(self.top_shift_var.get())
        
        # Save settings
        try:
            self.save_settings()
        except Exception:
            pass
        
        # Disable interface
        self.run_btn.config(state='disabled')
        self.clear_log()
        
        if visible_hide:
            self.log_message(f"🚀 Starting Visible&Hide processing: {os.path.basename(input_file)}")
            self.log_message(f"📁 Input file: {input_file}")
            self.log_message(f"⚙️ Parameters: font size={font_size}, shift={top_shift_px}px")
            self.log_message(f"🔄 Options: flip X={flip_x}, Y={flip_y}")
            self.log_message("=" * 60)
        else:
            if self.batch_files:
                self.log_message(f"🚀 Starting batch processing: {len(self.batch_files)} files")
            else:
                self.log_message(f"🚀 Starting processing: {os.path.basename(input_file)}")
                self.log_message(f"📁 Input file: {input_file}")
                self.log_message(f"📁 Output file: {output_file}")
            self.log_message(f"⚙️ Parameters: font size={font_size}, shift={top_shift_px}px")
            self.log_message(f"🔄 Options: hide text={hide_text}, flip X={flip_x}, Y={flip_y}")
            self.log_message("=" * 60)
        
        def build_output_paths_for(file_path: str):
            base_name = os.path.splitext(file_path)[0]
            suffix = "_searchable"
            if hide_text:
                suffix += "_Hide"
            return f"{base_name}{suffix}.pdf"

        def worker():
            try:
                if self.batch_files:
                    total = len(self.batch_files)
                    success = 0
                    for idx, in_file in enumerate(self.batch_files, start=1):
                        try:
                            self.log_message(f"[{idx}/{total}] 📁 Input file: {in_file}")
                            if visible_hide:
                                base_name = os.path.splitext(in_file)[0]
                                if base_name.endswith('_Hide'):
                                    base_name = base_name[:-5]
                                if base_name.endswith('_searchable'):
                                    base_name = base_name[:-11]

                                visible_output = f"{base_name}_searchable.pdf"
                                self.log_message(f"   → Visible: {os.path.basename(visible_output)}")
                                process_pdf(in_file, visible_output,
                                            hide_text=False,
                                            flip_x=flip_x,
                                            flip_y=flip_y,
                                            top_shift_px=top_shift_px,
                                            font_size=font_size,
                                            log_callback=self.log_message)

                                hide_output = f"{base_name}_searchable_Hide.pdf"
                                self.log_message(f"   → Hidden: {os.path.basename(hide_output)}")
                                process_pdf(in_file, hide_output,
                                            hide_text=True,
                                            flip_x=flip_x,
                                            flip_y=flip_y,
                                            top_shift_px=top_shift_px,
                                            font_size=font_size,
                                            log_callback=self.log_message)
                            else:
                                out_path = build_output_paths_for(in_file)
                                self.log_message(f"   → Output: {os.path.basename(out_path)}")
                                process_pdf(in_file, out_path,
                                            hide_text=hide_text,
                                            flip_x=flip_x,
                                            flip_y=flip_y,
                                            top_shift_px=top_shift_px,
                                            font_size=font_size,
                                            log_callback=self.log_message)
                            success += 1
                        except Exception as ie:
                            self.log_message(f"   ❌ Error on file: {ie}")
                    self.log_message(f"✅ Batch completed: {success}/{total} succeeded")
                    if success > 0 and messagebox.askyesno("Success", "Batch completed. Open output folder?"):
                        try:
                            folder = os.path.dirname(self.batch_files[0])
                            os.startfile(folder)
                        except Exception:
                            pass
                elif visible_hide:
                    # Create both versions
                    base_name = os.path.splitext(output_file)[0]
                    if base_name.endswith('_Hide'):
                        base_name = base_name[:-5]  # Remove _Hide suffix
                    if base_name.endswith('_searchable'):
                        base_name = base_name[:-11]  # Remove _searchable suffix
                    
                    # First: visible text version
                    visible_output = f"{base_name}_searchable.pdf"
                    self.log_message(f"📄 Creating visible text version: {os.path.basename(visible_output)}")
                    process_pdf(input_file, visible_output, 
                              hide_text=False, 
                              flip_x=flip_x, 
                              flip_y=flip_y, 
                              top_shift_px=top_shift_px, 
                              font_size=font_size,
                              log_callback=self.log_message)
                    
                    # Second: hidden text version
                    hide_output = f"{base_name}_searchable_Hide.pdf"
                    self.log_message(f"📄 Creating hidden text version: {os.path.basename(hide_output)}")
                    process_pdf(input_file, hide_output, 
                              hide_text=True, 
                              flip_x=flip_x, 
                              flip_y=flip_y, 
                              top_shift_px=top_shift_px, 
                              font_size=font_size,
                              log_callback=self.log_message)
                    
                    self.log_message("✅ Both versions created successfully!")
                    self.log_message(f"📄 Visible version: {visible_output}")
                    self.log_message(f"📄 Hidden version: {hide_output}")
                    
                    # Offer to open results
                    if messagebox.askyesno("Success", "Both versions created successfully!\nOpen results?"):
                        os.startfile(visible_output)
                        os.startfile(hide_output)
                else:
                    # Single version processing
                    process_pdf(input_file, output_file, 
                              hide_text=hide_text, 
                              flip_x=flip_x, 
                              flip_y=flip_y, 
                              top_shift_px=top_shift_px, 
                              font_size=font_size,
                              log_callback=self.log_message)
                    self.log_message("✅ Processing completed successfully!")
                    self.log_message(f"📄 Result saved: {output_file}")
                    
                    # Offer to open result
                    if messagebox.askyesno("Success", "Processing completed successfully!\nOpen result?"):
                        os.startfile(output_file)
                    
            except Exception as e:
                self.log_message(f"❌ Error: {str(e)}")
                messagebox.showerror("Error", f"Processing error:\n{str(e)}")
            finally:
                self.run_btn.config(state='normal')
        
        # Run in separate thread
        threading.Thread(target=worker, daemon=True).start()

def main():
    """Main function"""
    root = tk.Tk()
    app = ModernApp(root)
    
    # Handle window closing
    def on_closing():
        try:
            app.save_settings()
        except:
            pass
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == '__main__':
    main()
