#set document(title: "WGUPS Routing Program: Evidence Screenshots")
#set page(paper: "us-letter", margin: 1in)
#set text(size: 11pt)
#set par(justify: true, leading: 0.65em)

#align(center)[
  #text(size: 18pt, weight: "bold")[WGUPS Routing Program]
  #linebreak()
  #text(size: 14pt)[Evidence Screenshots]
  #linebreak()
  #v(0.5em)
  Student: bwhi880 \
  #datetime.today().display("[month repr:long] [day], [year]")
]

#v(1em)

The following figures show the program output at the times required by the scenario.

= Status Check at 8:35 a.m.

*Figure 1. Package status at 8:35 a.m.* All forty packages are visible on their assigned trucks. Packages 6, 9, 25, 28, and 32 appear in "delayed" status. Packages 2, 7, 14, 15, 16, 29, 33, and 34 are already delivered. Truck 1 is en route. Truck 2 packages remain at the hub because that truck does not depart until 9:05 a.m. Truck 3 packages also remain at the hub because that truck has not yet departed.

#image("screenshots/status-835am.png", width: 70%)

= Status Check at 9:35 a.m.

*Figure 2. Package status at 9:35 a.m.* Package 9 is still "delayed" because its address is not corrected until 10:20 a.m. Packages 6, 25, 28, and 32 are now "en route" or already delivered because Truck 2 departed at 9:05 a.m. Truck 3's packages remain "at hub" pending the 10:30 a.m. departure.

#image("screenshots/status-935am.png", width: 70%)

= Status Check at 12:03 p.m.

*Figure 3. Package status at 12:03 p.m.* All forty packages show "delivered at <time>" with no pending deliveries. Truck 3's last deliveries occurred around 11:10 a.m. to 11:46 a.m., confirming that the day ends only when every package has been served.

#image("screenshots/status-1203pm.png", width: 70%)

= Total Mileage

*Figure 4. Total mileage after complete execution.* The output header reads "Total mileage for all trucks: 89.3 miles," which is below the 140-mile requirement. Every package shows its final delivered status, truck assignment, and timestamp.

#image("screenshots/status-total-mileage.png", width: 70%)
