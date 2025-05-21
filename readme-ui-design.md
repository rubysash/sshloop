
## UI Design

The interface is split into two primary containers: **Left** and **Right**, each taking up 50% of the application window.

### Left Container

- **Row 1**:  
  `Load Hosts CSV` button to browse and load host data.

- **Row 2**:  
  `Treeview Table` displaying the loaded hosts with the following columns:
  - `IP`
  - `Port`
  - `Status` (updates dynamically as commands are executed)

  The treeview:
  - Uses left-aligned headers
  - Stretches vertically to fill the container
  - Updates each row status individually (e.g., "Complete", "Error")

- **Row 3**:
  "Description" field of the config/some.json contains explanation and instructions
  A text area displays this explanation.

---

### Right Container

A vertically stacked layout containing inputs, listboxes, previews, and outputs:

- **Row 1**:  
  `SSH Username` input field (defaulted to `"root"`)

- **Row 2**:  
  `Filter Commands` input box – filters available commands by keyword

- **Row 3**:  
  `Command Listbox` populated from categorized JSON command files  
  (Format: `CATEGORY: Command Label`)

- **Row 4**:  
  `Command Preview` (multi-line, read-only)  
  Displays the raw command associated with the selected entry

- **Row 5**:  
  `Manual Command` allows user to manually type a 1 shot command.   
  Should be a label, and entry field.
  IF there is any text here, it overrides the selection from json and gives warning before run command will fire.  "You are about to run a manual command, are you sure"?

- **Row 6**:  
  `Result Display Area`  
  Multi-line scrollable textbox showing parsed output and any errors for the selected host

- **Row 7**:  
  Horizontal `Button Row`:
  - `Run Command` – opens password prompt and starts execution
  - `Export` – saves results to `.xlsx` file and opens it
