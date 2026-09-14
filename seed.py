"""
Populate the database with starter content taken from the client
questionnaire, plus clearly-marked placeholder pricing/photos where the
client hasn't supplied final assets yet (packages pricing, gallery photos,
testimonials).

Run with:  python seed.py
Safe to re-run in development: it wipes and recreates tables each time.

SAFETY: against Postgres (staging/production), this script will NOT drop or
recreate tables — migrations own the schema there. It will only insert
starter rows, and only if you pass --i-understand-this-wipes-the-database,
and only if the relevant tables are currently empty (it refuses to run
twice and duplicate rows on top of real leads/testimonials).
"""
import os
import sys
from app import create_app
from extensions import db
from app.models import Product, Category, ServiceItem, Package, GalleryItem, Testimonial, User

app = create_app()

IS_POSTGRES = app.config.get("SQLALCHEMY_DATABASE_URI", "").startswith("postgresql")
CONFIRMED = "--i-understand-this-wipes-the-database" in sys.argv

if IS_POSTGRES and not CONFIRMED:
    print("Refusing to run: this database looks like Postgres (staging/production). "
          "Pass --i-understand-this-wipes-the-database to insert starter rows "
          "(schema/migrations are left untouched on Postgres).")
    sys.exit(1)

if not IS_POSTGRES and not CONFIRMED and os.environ.get("FLASK_CONFIG") == "production":
    print("Refusing to run with FLASK_CONFIG=production.")
    sys.exit(1)

with app.app_context():
    if IS_POSTGRES:
        if Category.query.first() is not None:
            print("Refusing to run: tables already contain data. This script only "
                  "seeds an empty database — delete existing rows manually first "
                  "if you really want to reseed.")
            sys.exit(1)
        # Schema already exists via migrations — do not drop/create tables here.
    else:
        db.drop_all()
        db.create_all()

    # ---- Admin user -----------------------------------------------------
    admin = User(name="Blazing Trail Admin", email="admin@blazingtrailengineering.com", role="admin")
    admin.set_password("ChangeMe123!")
    db.session.add(admin)

    # ---- Categories -------------------------------------------------------
    cat_solar = Category(name="Solar & Inverters", slug="solar-inverters", kind="product", icon="sun")
    cat_batteries = Category(name="Batteries", slug="batteries", kind="product", icon="battery")
    cat_panels = Category(name="Panels & Switchgear", slug="panels-switchgear", kind="product", icon="grid")
    cat_accessories = Category(name="Accessories & Protection", slug="accessories-protection", kind="product", icon="shield")
    db.session.add_all([cat_solar, cat_batteries, cat_panels, cat_accessories])
    db.session.flush()

    # ---- Products (from questionnaire section 2) --------------------------
    products = [
        Product(name="High-Efficiency Monocrystalline Solar Panel", slug="monocrystalline-solar-panel",
                short_description="High-output monocrystalline modules for residential, commercial and industrial arrays.",
                description=(
                    "Monocrystalline modules produce more power per square metre than polycrystalline "
                    "alternatives, which matters most on roofs where space is limited and every panel has "
                    "to earn its place. We select panels from established manufacturers and size the array "
                    "to your actual load, so you're not paying for capacity you'll never use, or short of "
                    "power on the days you need it most.\n\n"
                    "Every panel we supply is installed by our own technicians, mounted and wired to hold up "
                    "under Nigerian sun, wind and rain, not just to pass on installation day."
                ),
                spec_summary="Monocrystalline / high-efficiency", category=cat_solar, is_featured=True,
                image_url="images/products/solar-panel-monocrystalline.png"),
        Product(name="Hybrid Inverter System", slug="hybrid-inverter-system",
                short_description="Solar + grid + generator in one intelligent hybrid inverter.",
                description=(
                    "A hybrid inverter is the component that decides, moment to moment, whether your home or "
                    "business draws from solar, battery or the grid, and it switches between them automatically. "
                    "That means no manual changeover, no gap in power when the grid drops, and no wasted solar "
                    "generation during the day.\n\n"
                    "We size and configure the inverter to your battery bank and panel array as one system, "
                    "not as separately purchased parts that happen to be connected together, and we commission "
                    "it under real load before we call the job done."
                ),
                spec_summary="Hybrid / off-grid / grid-tied", category=cat_solar, is_featured=True,
                image_url="images/products/inverter-hybrid-wthd.jpeg"),
        Product(name="Off-Grid Inverter", slug="off-grid-inverter",
                short_description="Standalone power for sites with no reliable grid connection.",
                description=(
                    "For sites with no reliable grid connection at all, an off-grid inverter runs entirely on "
                    "solar and battery storage, sized so the system covers your actual daily consumption "
                    "rather than leaving you rationing power by evening.\n\n"
                    "We handle the full sizing calculation, factoring appliances, running hours and backup "
                    "days needed, so the system is built for genuine independence, not just a smaller version "
                    "of a grid-backup setup."
                ),
                spec_summary="Off-grid", category=cat_solar,
                image_url="images/products/inverter-off-grid-restarsolar.jpeg"),
        Product(name="Grid-Tied Inverter", slug="grid-tied-inverter",
                short_description="Feed solar generation straight into the grid connection.",
                description=(
                    "A grid-tied inverter feeds solar generation directly into your existing grid connection, "
                    "the most cost-effective setup where grid supply is reasonably stable and the goal is "
                    "reducing what you draw from it, not full independence.\n\n"
                    "We install and configure it to work safely alongside your existing electrical system, "
                    "with the protection and isolation the setup requires."
                ),
                spec_summary="Grid-tied", category=cat_solar,
                image_url="images/products/inverter-grid-tied-growatt.png"),
        Product(name="Lithium Battery Bank", slug="lithium-battery-bank",
                short_description="Long-cycle-life lithium storage for hybrid solar systems.",
                description=(
                    "Lithium batteries cost more upfront than tubular, and earn that back through a longer "
                    "service life, a smaller footprint, and a much deeper usable discharge, meaning more of "
                    "the battery's rated capacity is actually available to you day to day.\n\n"
                    "We size the bank to your inverter and expected backup duration, and install it with the "
                    "ventilation and access it needs to be serviced easily years from now, not just on day one."
                ),
                spec_summary="Lithium / deep cycle", category=cat_batteries, is_featured=True,
                image_url="images/products/battery-lithium-sunfit.jpeg"),
        Product(name="Tubular Battery Bank", slug="tubular-battery-bank",
                short_description="Reliable, cost-effective tubular batteries for backup power.",
                description=(
                    "Tubular batteries remain a proven, lower-upfront-cost option for backup power, well "
                    "suited to sites where budget matters more than footprint or the longest possible cycle "
                    "life.\n\n"
                    "We supply and install tubular banks sized to your load, with the same installation "
                    "standard, labelling and after-sales support as any lithium system we build."
                ),
                spec_summary="Tubular / flooded", category=cat_batteries,
                image_url="images/products/battery-tubular.jpg"),
        Product(name="Distribution Board", slug="distribution-board",
                short_description="Custom-built distribution boards for power routing and isolation.",
                description=(
                    "Distribution boards route and isolate power across a building or facility, and a poorly "
                    "specified one is a common source of nuisance trips, overloaded circuits and hard-to-trace "
                    "faults later on.\n\n"
                    "We fabricate boards in-house to your actual circuit layout and load, with breakers sized "
                    "to what they protect and every way clearly labelled, so a technician can identify a "
                    "circuit at a glance instead of guessing."
                ),
                spec_summary="Distribution / panel component", category=cat_panels, is_featured=True,
                image_url="images/products/distribution-board.jpeg"),
        Product(name="MCB / MCCB / ACB Circuit Breakers", slug="circuit-breakers",
                short_description="Miniature to air circuit breakers sized to your load profile.",
                description=(
                    "From miniature circuit breakers protecting a single lighting circuit to air circuit "
                    "breakers protecting an industrial main feed, breaker sizing is a calculation, not a "
                    "guess based on what's in stock.\n\n"
                    "We spec and supply breakers matched to the circuits they protect, whether that's a single "
                    "replacement unit or a full panel's worth for a new fabrication."
                ),
                spec_summary="MCB / MCCB / ACB", category=cat_panels,
                image_url="images/products/circuit-breakers-mcb.jpeg"),
        Product(name="Automatic Transfer Switch (ATS)", slug="ats-system",
                short_description="Seamless automatic changeover between grid, solar and generator.",
                description=(
                    "An ATS is what makes a hybrid power setup feel automatic instead of hands-on: when the "
                    "grid drops, it switches the load to generator or battery without anyone touching a "
                    "switch, and switches back once grid power is stable again.\n\n"
                    "We integrate ATS systems into new installations and existing setups alike, configured "
                    "for your specific combination of grid, solar, battery and generator."
                ),
                spec_summary="ATS / changeover", category=cat_panels, is_featured=True,
                image_url="images/products/ats-changeover-switch.jpg"),
        Product(name="Control & Protection Relays", slug="control-protection-relays",
                short_description="Relays and timers for control panels and protection schemes.",
                description=(
                    "Control and protection relays, including voltage protection, phase failure and phase "
                    "sequence relays, are what stop a voltage spike or a missing phase from taking out "
                    "equipment downstream.\n\n"
                    "We spec relays into new panel builds and retrofit them into existing systems where the "
                    "protection currently in place isn't enough for the load it's guarding."
                ),
                spec_summary="Control / protection", category=cat_accessories,
                image_url="images/products/relay-avr-voltage-protection.jpeg"),
        Product(name="Surge & Overload Protection Devices", slug="surge-overload-protection",
                short_description="Protect sensitive equipment from spikes and overload conditions.",
                description=(
                    "Surge and overload protection devices are inexpensive relative to what they protect: a "
                    "single voltage spike can take out an inverter, a fridge compressor, or a facility's "
                    "control electronics in an instant.\n\n"
                    "We install protection at the points in your system where it actually matters, sized to "
                    "the equipment and load it's guarding rather than added as an afterthought."
                ),
                spec_summary="Surge / overload protection", category=cat_accessories,
                image_url="images/products/surge-protector-britec.png"),
        Product(name="Energy Monitoring & Control Device", slug="energy-monitoring-device",
                short_description="Track consumption and generation in real time.",
                description=(
                    "An energy monitoring device gives you visibility into what your system is actually doing: "
                    "how much you're generating, how much you're consuming, and where the gap between the two "
                    "is coming from.\n\n"
                    "We integrate monitoring into new installations and existing systems so you're making "
                    "decisions about capacity, upgrades and usage from real numbers, not estimates."
                ),
                spec_summary="Monitoring / control", category=cat_accessories, is_featured=True,
                image_url="images/products/relay-avr-voltage-protection.jpeg"),
    ]
    db.session.add_all(products)

    # ---- Services (from questionnaire sections 2 & 3) ----------------------
    services = [
        ServiceItem(title="Solar System Design, Supply & Installation", order=1, icon="sun",
                    slug="solar-design-supply-installation",
                    summary="Residential, commercial and industrial solar, sized, supplied and installed end to end.",
                    description=(
                        "Most solar problems trace back to sizing, not equipment: a system built from a "
                        "rough guess instead of the building's actual load. We start every project with a "
                        "proper load assessment, then design, supply and install the panels, inverter and "
                        "battery as one integrated system, whether that's a family home, a retail branch, "
                        "or an industrial facility running production equipment.\n\n"
                        "Our own technicians handle the installation, not a subcontracted crew, and every "
                        "system is commissioned and tested under real load before we consider the job "
                        "finished. Support doesn't stop at handover either: we're available for optimisation "
                        "and troubleshooting long after the panels are up."
                    )),
        ServiceItem(title="Energy Audits & Load Assessment", order=2, icon="clipboard",
                    slug="energy-audits-load-assessment",
                    summary="Understand exactly what your building consumes before you spend on power.",
                    description=(
                        "Buying a power system before you know your actual consumption is how sites end up "
                        "either under-sized and rationing power, or over-sized and paying for capacity that "
                        "sits unused. We audit your appliances, running hours and peak demand, on-site or "
                        "through our sizing calculator, to establish exactly what your building needs.\n\n"
                        "That number becomes the basis for every recommendation we make, whether it's a "
                        "solar system, a backup power setup, or an upgrade to an existing installation. It's "
                        "the step that makes everything after it accurate instead of guesswork."
                    )),
        ServiceItem(title="Industrial Electrical Panel Fabrication", order=3, icon="grid",
                    slug="industrial-panel-fabrication",
                    summary="Distribution and control panels engineered and fabricated for industrial loads.",
                    description=(
                        "Off-the-shelf enclosures rarely match the layout, breaker sizing and protection an "
                        "industrial site actually needs. We design and fabricate distribution boards and "
                        "control panels in-house, built to the load and circuit layout of the facility "
                        "they're going into, not adapted from a generic template.\n\n"
                        "Every panel is wired, labelled and tested in our workshop before it reaches site, "
                        "so installation and commissioning go faster and the panel is easy to maintain years "
                        "after it's fitted."
                    )),
        ServiceItem(title="PLC Programming & Automation Integration", order=4, icon="cpu",
                    slug="plc-programming-automation",
                    summary="Programmable logic control for processes that need to run themselves reliably.",
                    description=(
                        "Power infrastructure and process control are usually treated as separate problems, "
                        "handled by separate contractors who don't talk to each other. We program and "
                        "integrate PLC-based automation directly alongside the electrical work, so control "
                        "logic and power supply are designed together instead of stitched together "
                        "afterward.\n\n"
                        "The result is automation that's actually reliable in production, because the person "
                        "who programmed the logic understood the electrical system it's running on."
                    )),
        ServiceItem(title="Backup Power & Hybrid Systems", order=5, icon="battery",
                    slug="backup-power-hybrid",
                    summary="Solar, inverter and generator working together instead of against each other.",
                    description=(
                        "Solar, battery and generator each cover a different gap: solar during the day, "
                        "battery through short outages, generator for extended ones. Run separately, they "
                        "leave you manually switching sources at the worst possible moment. We build "
                        "ATS-based hybrid systems that combine all three, so the changeover between them "
                        "happens automatically.\n\n"
                        "That means power stays on through a grid outage without anyone touching a switch, "
                        "and the system draws from whichever source makes the most sense at that moment."
                    )),
        ServiceItem(title="System Upgrades, Troubleshooting & Maintenance", order=6, icon="tool",
                    slug="upgrades-maintenance",
                    summary="Keep an existing system performing at the level it was designed for.",
                    description=(
                        "A power system that was correctly installed can still degrade in performance over "
                        "time: batteries age, connections loosen, loads grow beyond what the system was "
                        "originally sized for. We diagnose and fix systems already installed, whether we "
                        "built them or not, and carry out scheduled maintenance to catch problems before "
                        "they cause an outage.\n\n"
                        "If your current setup can no longer keep up with your load, we can also assess "
                        "and carry out the upgrade rather than recommend a full replacement by default."
                    )),
        ServiceItem(title="Power System Consulting & Advisory", order=7, icon="chart",
                    slug="power-consulting-advisory",
                    summary="Technical advisory for organisations planning power infrastructure at scale.",
                    description=(
                        "Larger power infrastructure decisions, grid integration, capacity planning, "
                        "multi-site standardisation, benefit from technical input before procurement starts, "
                        "not after equipment has already been bought. We provide advisory and consulting for "
                        "businesses making these decisions at scale, drawing on the same engineering "
                        "background behind every installation we carry out ourselves.\n\n"
                        "That means recommendations grounded in what actually gets built and maintained in "
                        "the field, not a report that looks good on paper and falls apart on-site."
                    )),
        ServiceItem(title="After-Sales Support & Optimisation", order=8, icon="headset",
                    slug="after-sales-support",
                    summary="Support doesn't end at commissioning.",
                    description=(
                        "A system that's correctly sized and installed can still underperform without "
                        "someone checking on it. We provide ongoing support after handover: monitoring "
                        "performance, adjusting settings as your load changes, and being reachable when "
                        "something needs attention rather than leaving you to figure it out alone.\n\n"
                        "It's included as part of how we work, not sold separately as a premium add-on, "
                        "because a system we stand behind is one we stay involved with."
                    )),
    ]
    db.session.add_all(services)

    # ---- Packages: real pricing from the client's price list -------------
    # "With panel" = inverter + battery + solar panels bundled.
    # "Without panel" = inverter + battery only (panels sourced separately).
    # 10kVA/15kWh has no confirmed price yet (client to provide), shown as
    # "Request quote" until then.
    packages = [
        # --- Lithium battery ---
        Package(name="3kVA Lithium System", slug="lithium-3kva-2-56kwh",
                kva_rating="3kVA", capacity_label="3kVA · 2.56kWh", battery_type="Lithium",
                tagline="Lithium: smallest system, no AC", order=1,
                price_with_panel_naira=1760000, price_without_panel_naira=None,
                panel_spec="3× 600W solar panels",
                includes="3kVA inverter\nLithium battery (2.56kWh)\n3× 600W solar panels (with-panel option)\nInstallation & commissioning",
                best_for="Basic home appliances, no AC"),
        Package(name="3.2kVA Lithium System", slug="lithium-3-2kva-2-5kwh",
                kva_rating="3.2kVA", capacity_label="3.2kVA · 2.5kWh", battery_type="Lithium",
                tagline="Lithium: compact backup for a small home", order=2,
                price_with_panel_naira=1750000, price_without_panel_naira=1250000,
                panel_spec="4× 330W solar panels",
                includes="3.2kVA inverter\nLithium battery (2.5kWh)\n4× 330W solar panels (with-panel option)\nInstallation & commissioning",
                best_for="Small apartments, essential appliances & lighting"),
        Package(name="4.2kVA Lithium System (2.5kWh)", slug="lithium-4-2kva-2-5kwh",
                kva_rating="4.2kVA", capacity_label="4.2kVA · 2.5kWh", battery_type="Lithium",
                tagline="Lithium: everyday home backup", order=3,
                price_with_panel_naira=1810000, price_without_panel_naira=1310000,
                panel_spec="4× 330W solar panels",
                includes="4.2kVA inverter\nLithium battery (2.5kWh)\n4× 330W solar panels (with-panel option)\nInstallation & commissioning",
                best_for="Homes running fridge, TVs and lighting through outages"),
        Package(name="4.2kVA Lithium System (5kWh)", slug="lithium-4-2kva-5kwh",
                kva_rating="4.2kVA", capacity_label="4.2kVA · 5kWh", battery_type="Lithium",
                tagline="Lithium: longer backup time", order=4,
                price_with_panel_naira=2610000, price_without_panel_naira=1730000,
                includes="4.2kVA inverter\nLithium battery (5kWh)\nInstallation & commissioning",
                best_for="Homes wanting extended backup hours on the same load"),
        Package(name="6kVA Lithium System (10kWh)", slug="lithium-6kva-10kwh",
                kva_rating="6kVA", capacity_label="6kVA · 10kWh", battery_type="Lithium",
                tagline="Lithium: 1 AC, longer backup time", order=5,
                price_with_panel_naira=3710000, price_without_panel_naira=None,
                panel_spec="6× 600W solar panels",
                includes="6kVA inverter\nLithium battery (10kWh)\n6× 600W solar panels (with-panel option)\nInstallation & commissioning",
                best_for="Basic home appliances and 1 AC, longer backup time"),
        Package(name="6.2kVA Lithium System (5kWh)", slug="lithium-6-2kva-5kwh",
                kva_rating="6.2kVA", capacity_label="6.2kVA · 5kWh", battery_type="Lithium",
                tagline="Lithium: AC-ready home or small office", order=6,
                is_popular=True,
                price_with_panel_naira=2710000, price_without_panel_naira=1900000,
                panel_spec="4× 600W solar panels",
                includes="6.2kVA inverter\nLithium battery (5kWh)\n4× 600W solar panels (with-panel option)\nInstallation & commissioning",
                best_for="Family homes or small offices running AC units"),
        Package(name="6.2kVA Lithium System (10kWh)", slug="lithium-6-2kva-10kwh",
                kva_rating="6.2kVA", capacity_label="6.2kVA · 10kWh", battery_type="Lithium",
                tagline="Lithium: heavier load, longer backup", order=7,
                price_with_panel_naira=3910000, price_without_panel_naira=2950000,
                panel_spec="6× 600W solar panels",
                includes="6.2kVA inverter\nLithium battery (10kWh)\n6× 600W solar panels (with-panel option)\nInstallation & commissioning",
                best_for="Larger homes or businesses needing extended runtime"),
        Package(name="6.2kVA Lithium System (15kWh)", slug="lithium-6-2kva-15kwh",
                kva_rating="6.2kVA", capacity_label="6.2kVA · 15kWh", battery_type="Lithium",
                tagline="Lithium: maximum backup on this rating", order=8,
                price_with_panel_naira=4550000, price_without_panel_naira=3480000,
                panel_spec="9× 600W solar panels",
                includes="6.2kVA inverter\nLithium battery (15kWh)\n9× 600W solar panels (with-panel option)\nInstallation & commissioning",
                best_for="High-demand homes or businesses wanting near-uninterrupted power"),
        Package(name="10kVA Lithium System (15kWh)", slug="lithium-10kva-15kwh",
                kva_rating="10kVA", capacity_label="10kVA · 15kWh", battery_type="Lithium",
                tagline="Lithium: commercial-scale backup", order=9,
                price_with_panel_naira=5900000, price_without_panel_naira=None,
                panel_spec="12× 600W solar panels",
                includes="10kVA inverter\nLithium battery (15kWh)\n12× 600W solar panels (with-panel option)\nInstallation & commissioning",
                best_for="Basic home appliances and at least 2 ACs, small commercial premises with high daily power demand"),

        # --- Tubular battery ---
        Package(name="1kVA Tubular System", slug="tubular-1kva",
                kva_rating="1kVA", capacity_label="1kVA", battery_type="Tubular",
                tagline="Tubular: budget-friendly essentials backup", order=10,
                price_with_panel_naira=1880000, price_without_panel_naira=570000,
                panel_spec="3× 220W solar panels",
                includes="1kVA inverter\nTubular battery\n3× 220W solar panels (with-panel option)\nInstallation & commissioning",
                best_for="A few rooms: lighting, fans, TV, router"),
        Package(name="2.5kVA Tubular System", slug="tubular-2-5kva",
                kva_rating="2.5kVA", capacity_label="2.5kVA", battery_type="Tubular",
                tagline="Tubular: reliable small-home backup", order=11,
                price_with_panel_naira=1510000, price_without_panel_naira=900000,
                panel_spec="4× 330W solar panels",
                includes="2.5kVA inverter\nTubular battery\n4× 330W solar panels (with-panel option)\nInstallation & commissioning",
                best_for="Small homes running fridge, fans and lighting"),
        Package(name="3.2kVA Tubular System", slug="tubular-3-2kva",
                kva_rating="3.2kVA", capacity_label="3.2kVA", battery_type="Tubular",
                tagline="Tubular: proven, budget-conscious backup", order=12,
                price_with_panel_naira=1580000, price_without_panel_naira=1000000,
                panel_spec="4× 330W solar panels",
                includes="3.2kVA inverter\nTubular battery\n4× 330W solar panels (with-panel option)\nInstallation & commissioning",
                best_for="Small apartments, essential appliances & lighting"),
        Package(name="4.2kVA Tubular System", slug="tubular-4-2kva",
                kva_rating="4.2kVA", capacity_label="4.2kVA", battery_type="Tubular",
                tagline="Tubular: everyday home backup", order=13,
                price_with_panel_naira=1680000, price_without_panel_naira=1080000,
                panel_spec="4× 330W solar panels",
                includes="4.2kVA inverter\nTubular battery\n4× 330W solar panels (with-panel option)\nInstallation & commissioning",
                best_for="Homes running fridge, TVs and lighting through outages"),
        Package(name="5kVA Tubular System", slug="tubular-5kva",
                kva_rating="5kVA", capacity_label="5kVA", battery_type="Tubular",
                tagline="Tubular: AC-ready on a tubular budget", order=14,
                price_with_panel_naira=2650000, price_without_panel_naira=1900000,
                panel_spec="5× 600W solar panels",
                includes="5kVA inverter\nTubular battery\n5× 600W solar panels (with-panel option)\nInstallation & commissioning",
                best_for="Family homes or small offices running AC units"),
    ]
    db.session.add_all(packages)

    # ---- Gallery: real project photos, supplied by the client -------------
    # Photos are genuine installs; only "panels" (industrial panel
    # fabrication) and "plc" (automation) have no real photos yet, so those
    # filter categories are left empty on purpose rather than filled with
    # stock/placeholder images. The empty state ("No projects in this
    # category yet") already handles that gracefully.
    #
    # description/highlights power the click-through detail page
    # (gallery.html?id=N): a short sell paragraph plus a few concrete
    # reasons the work matters, ending in a CTA on the page itself.
    gallery_items = [
        # -- Rooftop solar arrays --
        GalleryItem(title="Rooftop Solar Array: Lekki Skyline View", category="solar", location="Lagos",
                    kva_rating="Rooftop array", is_featured=True, image_url="images/gallery/solar-rooftop-array-01.jpeg",
                    description=(
                        "A full rooftop array engineered for a Lekki residence, sited and angled for maximum "
                        "sun exposure over the property's skyline. The panels are mounted flush and low-profile, "
                        "so the array adds capacity without changing the look of the roofline."
                    ),
                    highlights=(
                        "High-efficiency monocrystalline panels for more output per square metre of roof\n"
                        "Mounting engineered for Lagos wind and rain loads, not a generic bracket kit\n"
                        "Sized from an actual load assessment of the home, not a standard package"
                    )),
        GalleryItem(title="Rooftop Solar Installation", category="solar", location="Lagos",
                    kva_rating="Rooftop array", image_url="images/gallery/solar-rooftop-array-02.jpeg",
                    description=(
                        "A residential rooftop array supplied and installed end to end, from racking to final "
                        "commissioning. Cable runs are routed and clipped along the roofline rather than left "
                        "loose, which is the difference between an installation and a proper one."
                    ),
                    highlights=(
                        "Design, supply and installation handled by one team, not separate contractors\n"
                        "Clean cable management and grounding, inspected before handover\n"
                        "Commissioned and tested under real load before we call it done"
                    )),
        GalleryItem(title="Rooftop Solar Installation, Residential Estate", category="solar", location="Lagos",
                    kva_rating="Rooftop array", image_url="images/gallery/solar-rooftop-array-03.webp",
                    description=(
                        "An estate-home installation, where roof access and neighbouring structures make layout "
                        "planning matter more than usual. The array was laid out to clear shading from nearby "
                        "rooflines through the day, not just at the time of the site visit."
                    ),
                    highlights=(
                        "Shading and roof geometry accounted for before panels went up\n"
                        "Estate-appropriate finish: no exposed conduit, no visible clutter\n"
                        "Backed by after-sales support, not just a one-time install"
                    )),
        GalleryItem(title="Rooftop Solar Installation, Upscale Residence", category="solar", location="Lagos",
                    kva_rating="Rooftop array", image_url="images/gallery/solar-rooftop-array-04.webp",
                    description=(
                        "A higher-capacity system for a home with real daytime and evening demand: air "
                        "conditioning, multiple fridges, entertainment systems, all covered without the home "
                        "quietly rationing power the moment the grid drops."
                    ),
                    highlights=(
                        "Sized for AC-heavy households, not just lights and fans\n"
                        "Hybrid setup keeps solar, battery and grid working together automatically\n"
                        "One point of contact for design, installation and support after handover"
                    )),
        GalleryItem(title="Rooftop Solar Panel Close-Up", category="solar", location="Lagos",
                    kva_rating="Rooftop array", image_url="images/gallery/solar-rooftop-array-05.webp",
                    description=(
                        "A closer look at the panel and mounting hardware itself: uniform row spacing, "
                        "properly torqued clamps, and cable runs dressed flat against the rail rather than "
                        "flapping loose in the wind."
                    ),
                    highlights=(
                        "Monocrystalline modules chosen for output, not just lowest unit price\n"
                        "Mounting hardware rated for the rooftop it's installed on\n"
                        "The details you don't see from the ground are where installs fail early"
                    )),
        GalleryItem(title="Rooftop Solar Array, Wide Installation", category="solar", location="Lagos",
                    kva_rating="Rooftop array", is_featured=True, image_url="images/gallery/solar-rooftop-array-06.webp",
                    description=(
                        "A large-format rooftop array covering the full usable roof area of the property. "
                        "Bigger arrays raise the stakes on layout and wiring discipline, since a mistake "
                        "repeated across dozens of panels is a lot more expensive than one made on a small job."
                    ),
                    highlights=(
                        "Full-roof coverage planned around vents, water tanks and roof access points\n"
                        "String design balanced so one shaded panel doesn't drag down the whole array\n"
                        "Built to scale with future load growth, not maxed out on day one"
                    )),
        GalleryItem(title="Rooftop Solar Array, Residential Complex", category="solar", location="Lagos",
                    kva_rating="Rooftop array", image_url="images/gallery/solar-rooftop-array-07.webp",
                    description=(
                        "Solar for a multi-unit residential complex, where the system has to serve shared "
                        "expectations across several households rather than one owner's preferences alone."
                    ),
                    highlights=(
                        "Designed to handle the load pattern of a multi-unit property, not a single flat\n"
                        "Installed with minimal disruption to residents during the build\n"
                        "Maintenance and troubleshooting available after commissioning, on call"
                    )),
        GalleryItem(title="Ground-Mount Solar Carport", category="solar", location="Lagos",
                    kva_rating="Ground-mount", is_featured=True, image_url="images/gallery/solar-ground-mount-carport.webp",
                    description=(
                        "A ground-mounted carport array: the panels double as covered parking while generating "
                        "power, a practical option when roof space is limited, shaded, or better left for other use."
                    ),
                    highlights=(
                        "Turns unused yard or parking space into a power asset\n"
                        "Structural steel frame engineered for the array's weight and wind load, not a lean-to\n"
                        "A practical fit where roof pitch, shading or access rules out rooftop mounting"
                    )),
        GalleryItem(title="Solar Panel Mounting in Progress", category="solar", location="Lagos",
                    kva_rating="Rooftop array", image_url="images/gallery/solar-rooftop-mounting-crew.jpeg",
                    description=(
                        "Our crew mid-install, mounting rail and racking ahead of the panels going up. We're "
                        "happy to show the process, not just the finished shot, because the mounting work "
                        "underneath is what actually determines how the system holds up over years, not weeks."
                    ),
                    highlights=(
                        "Our own technicians on site, not a subcontracted crew\n"
                        "Racking secured and levelled before a single panel is fitted\n"
                        "What's under the panels matters as much as the panels themselves"
                    )),

        # -- Hybrid/off-grid inverter & battery installations --
        GalleryItem(title="Hybrid Inverter & Lithium Battery Installation", category="backup", location="Lagos",
                    kva_rating="Indoor install", is_featured=True, image_url="images/gallery/solar-battery-system-wthd.jpeg",
                    description=(
                        "A hybrid inverter paired with a lithium battery bank, wall-mounted and wired into the "
                        "home's distribution board so switchover between grid, solar and battery happens "
                        "automatically, with nobody running to flip a changeover switch when the power goes."
                    ),
                    highlights=(
                        "Lithium storage: longer cycle life and deeper usable discharge than tubular\n"
                        "Automatic switchover, no manual intervention when the grid drops\n"
                        "Neatly wall-mounted with labelled breakers, not a tangle of loose cable"
                    )),
        GalleryItem(title="Hybrid Inverter & Battery Installation", category="backup", location="Lagos",
                    kva_rating="Indoor install", image_url="images/gallery/solar-battery-system-wthd-02.webp",
                    description=(
                        "Another angle on a hybrid inverter and battery setup, showing the finished enclosure "
                        "and wiring once commissioning was complete."
                    ),
                    highlights=(
                        "Installed, tested and commissioned by our technicians on-site\n"
                        "Battery and inverter sized together, not mismatched to save cost\n"
                        "Backed by after-sales support if anything needs adjusting"
                    )),
        GalleryItem(title="Hybrid Inverter & Battery Installation", category="backup", location="Lagos",
                    kva_rating="Indoor install", image_url="images/gallery/solar-battery-system-ensky.jpeg",
                    description=(
                        "A hybrid inverter and battery system built around Ensky components, chosen for this "
                        "site's budget and expected load without cutting corners on the installation itself."
                    ),
                    highlights=(
                        "Component brand matched to the client's budget and expected runtime\n"
                        "Full commissioning and load test before handover\n"
                        "Same installation standard regardless of which brand of equipment is used"
                    )),
        GalleryItem(title="Hybrid Inverter & Battery Installation", category="backup", location="Lagos",
                    kva_rating="Indoor install", image_url="images/gallery/solar-battery-system-ensky-03.webp",
                    description=(
                        "A second Ensky-based hybrid system, installed indoors with clear access for future "
                        "maintenance, since a battery bank that's hard to reach is a battery bank that doesn't "
                        "get serviced."
                    ),
                    highlights=(
                        "Positioned for easy access during future servicing, not squeezed into a corner\n"
                        "Ventilation considered at install, not left as an afterthought\n"
                        "Part of a system, not a standalone box: solar, battery and grid work together"
                    )),
        GalleryItem(title="Off-Grid Inverter & LiFePO4 Battery Installation", category="backup", location="Lagos",
                    kva_rating="Indoor install", is_featured=True, image_url="images/gallery/solar-battery-system-restarsolar.jpeg",
                    description=(
                        "A fully off-grid setup built around a Restarsolar inverter and LiFePO4 battery bank, "
                        "for a site where the goal is independence from the grid rather than simply backing it up."
                    ),
                    highlights=(
                        "LiFePO4 chemistry: safer thermal profile and a long service life\n"
                        "Designed to run independently, not just bridge grid outages\n"
                        "Right-sized to the site's actual daily consumption, avoiding an oversized, overpriced bank"
                    )),
        GalleryItem(title="Indoor Inverter Installation", category="backup", location="Lagos",
                    kva_rating="Indoor install", image_url="images/gallery/solar-indoor-install.jpeg",
                    description=(
                        "A straightforward indoor inverter installation, wall-mounted with breakers labelled and "
                        "cabling run through conduit rather than left exposed across the floor."
                    ),
                    highlights=(
                        "Labelled breakers so anyone on site can identify a circuit at a glance\n"
                        "Conduit-run cabling, not loose wire underfoot\n"
                        "Installed to last, not just to pass a first inspection"
                    )),
        GalleryItem(title="Inverter & Battery Installation, Utility Closet", category="backup", location="Lagos",
                    kva_rating="Indoor install", image_url="images/gallery/inverter-battery-ensky-02.webp",
                    description=(
                        "An inverter and battery bank fitted into a dedicated utility closet, keeping the "
                        "equipment out of living space while staying accessible for maintenance."
                    ),
                    highlights=(
                        "Compact layout that respects limited utility space\n"
                        "Ventilation and access maintained despite the tighter footprint\n"
                        "Wiring routed cleanly rather than crammed in around the equipment"
                    )),
        GalleryItem(title="Inverter & Battery Installation", category="backup", location="Lagos",
                    kva_rating="Indoor install", image_url="images/gallery/inverter-battery-euromet-onyx.webp",
                    description=(
                        "A Euromet Onyx inverter and battery installation, specified to match the client's "
                        "load profile after a proper energy audit rather than a guess at what \"should\" work."
                    ),
                    highlights=(
                        "Specified from a real load assessment, not a standard package pushed regardless of fit\n"
                        "Installed with the same wiring and labelling standard on every job\n"
                        "Supported after handover, not left to figure out alone"
                    )),
        GalleryItem(title="Inverter & Battery Installation", category="backup", location="Lagos",
                    kva_rating="Indoor install", image_url="images/gallery/inverter-battery-restarsolar-luxsun.webp",
                    description=(
                        "A Restarsolar inverter paired with a LuxSun battery bank, installed and commissioned "
                        "as one integrated system rather than two components bolted together."
                    ),
                    highlights=(
                        "Inverter and battery matched for compatible charge and discharge rates\n"
                        "Full system commissioning, not just a plug-in and walk-away\n"
                        "One team accountable for the whole install, start to finish"
                    )),
        GalleryItem(title="Inverter & Battery Installation", category="backup", location="Lagos",
                    kva_rating="Indoor install", image_url="images/gallery/inverter-battery-sako.webp",
                    description=(
                        "A Sako inverter and battery system, installed for a client prioritising a reliable, "
                        "cost-conscious backup solution over the highest-spec option on the market."
                    ),
                    highlights=(
                        "Sized to genuine need, not upsold beyond what the site requires\n"
                        "Full installation and commissioning included, not just equipment supply\n"
                        "Available for troubleshooting and optimisation after installation"
                    )),
        GalleryItem(title="Inverter & Battery Installation", category="backup", location="Lagos",
                    kva_rating="Indoor install", image_url="images/gallery/inverter-battery-install-03.webp",
                    description=(
                        "Another completed inverter and battery installation, showing the standard of "
                        "wall-mounting, cable dressing and labelling applied across every backup power job we do."
                    ),
                    highlights=(
                        "Same installation standard whether the job is small or large\n"
                        "Tested under load before we consider the job finished\n"
                        "Clean, inspectable wiring, not hidden behind a cover plate"
                    )),
        GalleryItem(title="Inverter & Battery Installation", category="backup", location="Lagos",
                    kva_rating="Indoor install", image_url="images/gallery/inverter-battery-ipower-restarsolar.webp",
                    description=(
                        "An iPower and Restarsolar combination installed as a backup power system, supplied "
                        "and fitted by our technicians from procurement through to commissioning."
                    ),
                    highlights=(
                        "Procurement, installation and commissioning handled as one job\n"
                        "Battery and inverter pairing checked for compatibility before install\n"
                        "Backed by the same after-sales support as every other project here"
                    )),

        # -- Panel fabrication --
        GalleryItem(title="Industrial Distribution Panel", category="panels", location="Lagos",
                    kva_rating="Panel fabrication", is_featured=True, image_url="images/gallery/distribution-panel-01.jpeg",
                    description=(
                        "A custom-fabricated distribution panel built for an industrial power distribution "
                        "requirement, not adapted from an off-the-shelf enclosure. Layout, breaker sizing and "
                        "labelling are all specified to the site's actual load, not a generic template."
                    ),
                    highlights=(
                        "Fabricated in-house to the site's load and layout, not off-the-shelf\n"
                        "Breakers and protection devices sized to the circuits they serve\n"
                        "Every way labelled clearly, so a technician can trace a fault fast"
                    )),
        GalleryItem(title="Distribution Panel, Input/Output Wiring", category="panels", location="Lagos",
                    kva_rating="Panel fabrication", image_url="images/gallery/distribution-panel-02.jpeg",
                    description=(
                        "A closer view of the input and output wiring inside a fabricated distribution panel, "
                        "showing the routing and terminations before the panel was closed up and commissioned."
                    ),
                    highlights=(
                        "Wiring routed and bundled for airflow and future access, not just to fit\n"
                        "Terminations torqued and checked before commissioning, not just visually inspected\n"
                        "Built to be maintained for years, not just to pass the first switch-on"
                    )),
        GalleryItem(title="Motor Starter Control Panel", category="panels", location="Lagos",
                    kva_rating="Panel fabrication", image_url="images/gallery/motor-starter-panel.jpeg",
                    description=(
                        "A motor starter control panel fabricated for an industrial motor load, combining "
                        "contactors, overload protection and control wiring in one enclosure built to the "
                        "motor's actual starting and running characteristics."
                    ),
                    highlights=(
                        "Contactors and overload protection sized to the motor's real starting current\n"
                        "Control and power wiring kept separate and clearly identified\n"
                        "Fabricated and tested before it ever reaches site"
                    )),
        GalleryItem(title="Motor Starter Panel, Internal Wiring", category="panels", location="Lagos",
                    kva_rating="Panel fabrication", image_url="images/gallery/motor-starter-panel-interior.jpeg",
                    description=(
                        "Inside a motor starter panel, showing the relay, timer and contactor wiring that "
                        "makes the starting sequence work reliably every time the motor is called on to run."
                    ),
                    highlights=(
                        "Relays and timers wired and tested before the panel leaves our workshop\n"
                        "Clean internal layout that makes future troubleshooting straightforward\n"
                        "Built by the same team that can service it later, not a one-off fabricator"
                    )),
    ]
    db.session.add_all(gallery_items)

    # ---- Testimonials: 22 real Google reviews, supplied by the client ----
    # Newest first (per client instruction): sort_rank ascending = newest.
    # Owner replies are the client's own, taken verbatim from Google.
    testimonials = [
        Testimonial(client_name="Mohammed Hassan Ojoh", quote=(
            "Absolutely the best Inverter and Solar installation Company. They also have "
            "hands on experience expect with inverter installation."),
            source="Google Review", reviewer_meta="1 review", review_date_label="3 weeks ago",
            sort_rank=1, status="approved"),
        Testimonial(client_name="Akinnibosun Bukola", quote=(
            "I got quality items ,prompt delivery, great services from the blazing trail "
            "and the service was great.i highly recommend"),
            source="Google Review", reviewer_meta="1 review · 2 photos", review_date_label="a month ago",
            sort_rank=2, status="approved"),
        Testimonial(client_name="jennifer subi", quote=(
            "I had a great experience working with Blazing Trail Solar. They are highly "
            "professional and did an excellent job with the installation. The team took the "
            "time to thoroughly explain the pros and cons of the available options, ensuring "
            "I had all the information needed to make an informed decision within my budget. "
            "What stood out most was their solution-oriented approach. Even when we "
            "encountered some challenges related to my building, they remained patient, "
            "proactive, and committed to finding the best solution. Their customer service is "
            "exceptional, and their follow-up process is impressive; they still check in "
            "months later to ensure I am satisfied with their product and service. I highly "
            "recommend them to anyone looking for quality service, professionalism, and "
            "outstanding customer care."),
            owner_reply="We are very grateful for your kind words. We also remain committed to giving the best possible service.",
            source="Google Review", reviewer_meta="2 reviews", review_date_label="a month ago",
            sort_rank=3, status="approved", is_featured=True),
        Testimonial(client_name="shem Kay", quote=(
            "It'll be 2 weeks of uninterrupted power supply since the installation.. Blazin "
            "Trail was very supportive with creating my solution based on load while making "
            "room to scale the capacity of the system cost effective.."),
            owner_reply="It brings us immense pleasure that you and your family are satisfied with our work and service. Thank you for your patronage.",
            source="Google Review", reviewer_meta="2 reviews", review_date_label="6 months ago",
            sort_rank=4, status="approved", is_featured=True),
        Testimonial(client_name="isaiah chidi", quote=(
            "Good customer relations , very calm , professional to d core,patient and timely "
            "delivery,will recommend him anytime and any day. Well done Blazing Trail Solar "
            ",u are d best! \U0001F4AA"),
            owner_reply="Thank you so much for your patronage and kind words. We are glad to have been able to listen to your need and deliver accordingly. Regards.",
            source="Google Review", reviewer_meta="1 review", review_date_label="6 months ago",
            sort_rank=5, status="approved"),
        Testimonial(client_name="Anthony Emebo", quote=(
            "This is a professional brand and they did really well with solar installation "
            "for me recently. They provided good information on how the system works and "
            "helped me make an informed decision. I would highly recommend"),
            owner_reply="Thank you for trusting us to deliver.",
            source="Google Review", review_date_label="8 months ago",
            sort_rank=6, status="approved"),
        Testimonial(client_name="King-Solomon Evbogbai", quote=(
            "Very happy with my installation! Delivery was timely, service was reliable and "
            "installation was well done."),
            owner_reply="Thank you for your trust in our services.",
            source="Google Review", reviewer_meta="Local Guide · 32 reviews · 3 photos", review_date_label="8 months ago",
            sort_rank=7, status="approved", is_featured=True),
        Testimonial(client_name="Eugene Opeyemi", quote=(
            "Had a great experience, installed solar panels works like a peach .. and seem "
            "highly durable"),
            owner_reply="Thank you Mr Eugene. We are delighted you had a great experience with us. Hopefully you refer us to other clients. Regards.",
            source="Google Review", reviewer_meta="1 review", review_date_label="8 months ago",
            sort_rank=8, status="approved"),
        Testimonial(client_name="Zachary Raymond", quote="Great service, very helpful staff! Highly recommend.",
            owner_reply="We are always at your service sir.",
            source="Google Review", reviewer_meta="1 review", review_date_label="8 months ago",
            sort_rank=9, status="approved"),
        Testimonial(client_name="Benjamin opiah", quote=(
            "Wonderful services! I would recommend any day! Thank you Blazing Trail."),
            owner_reply="You are most welcome Mr. Ben. Thanks for your support",
            source="Google Review", reviewer_meta="1 review", review_date_label="8 months ago",
            sort_rank=10, status="approved"),
        Testimonial(client_name="Timothy okocha", quote="I recommend, quality products",
            source="Google Review", reviewer_meta="2 reviews", review_date_label="8 months ago",
            sort_rank=11, status="approved"),
        Testimonial(client_name="Ibrahim Ayodele", quote=(
            "Excellent products. Looking forward to doing business with them . Solid \U0001F4AF"),
            owner_reply="Thank you so much Mr Ibrahim. We are always at your service.",
            source="Google Review", reviewer_meta="1 review", review_date_label="Edited 8 months ago",
            sort_rank=12, status="approved"),
        Testimonial(client_name="Oluwaseun Oyedeji", quote=(
            "Great experience buying from Blazing Trail Nigeria. The Power box I got is "
            "fantastic and works perfectly. Highly recommend."),
            owner_reply="Thank you very much for your patronage.",
            source="Google Review", reviewer_meta="1 review", review_date_label="10 months ago",
            sort_rank=13, status="approved"),
        Testimonial(client_name="Gerard Chibor", quote="Their service is great.",
            source="Google Review", review_date_label="Edited 10 months ago",
            sort_rank=14, status="approved"),
        Testimonial(client_name="Chukwudi Hyginus", quote="Good customer service Very recommended Try it out \U0001F44D",
            source="Google Review", reviewer_meta="1 review", review_date_label="11 months ago",
            sort_rank=15, status="approved"),
        Testimonial(client_name="Okafor munachi Alexander", quote="He is a good supplier",
            source="Google Review", reviewer_meta="1 review", review_date_label="11 months ago",
            sort_rank=16, status="approved"),
        Testimonial(client_name="sussan cas", quote=(
            "I got quality electrical products from Blazing trail and the customer service "
            "was great. I highly recommend"),
            owner_reply="Thank you for your patronage",
            source="Google Review", reviewer_meta="2 reviews", review_date_label="a year ago",
            sort_rank=17, status="approved"),
        Testimonial(client_name="Daberechi Eke", quote="Quality items, prompt delivery. Great service in general",
            owner_reply="Thank you very much for your patronage.",
            source="Google Review", reviewer_meta="Local Guide · 138 reviews · 6 photos", review_date_label="a year ago",
            sort_rank=18, status="approved"),
        Testimonial(client_name="Ayo Salawu", quote="Fantastic product and service! Great job done",
            owner_reply="I am beyond excited that you are satisfied with our products and services. Thank you for your patronage.",
            source="Google Review", reviewer_meta="2 reviews", review_date_label="a year ago",
            sort_rank=19, status="approved"),
        Testimonial(client_name="Kufre Markson", quote="Highly recommended services on sales, installations and delivery.",
            source="Google Review", reviewer_meta="1 review", review_date_label="a year ago",
            sort_rank=20, status="approved"),
        Testimonial(client_name="James Nkwocha", quote="Procurement and delivery of equipments was prompt and professional.",
            owner_reply="I am glad you have found us very helpful and look forward to doing further business with you.",
            source="Google Review", reviewer_meta="1 review", review_date_label="a year ago",
            sort_rank=21, status="approved"),
        Testimonial(client_name="3rty", quote="Very professional and always willing to help.",
            owner_reply="Always at your service. Thank you sir.",
            source="Google Review", reviewer_meta="Local Guide · 3 reviews", review_date_label="a year ago",
            sort_rank=22, status="approved"),
    ]
    db.session.add_all(testimonials)

    db.session.commit()
    print("Database seeded.")
    print("Admin login -> email: admin@blazingtrailengineering.com  password: ChangeMe123!")
    print("CHANGE THIS PASSWORD before deploying.")
