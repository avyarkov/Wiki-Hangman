#!/usr/bin/env python3
"""Builds list-science.json from the validated candidate pool.

Two kinds of removal, kept separate on purpose:

  STRUCTURAL  the game cannot use these at all -- roundup pages with no real
              subject, and titles with under three distinct a-z letters, which
              the A-Z keyboard would solve in one or two presses.

  OBSCURE     judged past the bar of "a student in any science major would
              recognise this". Every entry here also sits in the weak tail of
              the measurements (low pageviews AND few language editions); the
              measurement chooses the candidates, judgement only decides which
              of those weak-signal titles are genuinely specialist. Nothing
              above the tail is cut on taste alone.

  UNGUESSABLE fine as science, bad as a hangman word: the answer can only be
              reached by recalling its spelling letter by letter, because no
              amount of partial reveal narrows it down. Both lists here are
              deliberately short -- the recognisable members are rescued, so
              Homo erectus survives while Caenorhabditis elegans does not, and
              NASA survives while EXPTIME does not.
"""

import json
import re
import sys

STRUCTURAL_PREFIX = ("List of ", "Glossary of ", "Timeline of ")

# Latin binomials and Latin-form clade names. Common-name biology vocabulary
# (Arthropod, Cephalopod, Trilobite) and the household dinosaur genera are not
# here -- they are ordinary English words that happen to descend from Latin.
LATIN_NAME = """
Ammonoidea
Arabidopsis thaliana
Caenorhabditis elegans
Cnidaria
Drosophila melanogaster
Escherichia coli
Hominidae
Machairodontinae
Mollusca
Saccharomyces cerevisiae
""".split("\n")

# Acronyms with no everyday currency. The other 48 acronym titles in the pool
# (NASA, CERN, DNA, JSON, HTTP, CRISPR, LIGO, MOSFET, ENIAC, ALGOL ...) stay.
ACRONYM_ONLY = """
BQP
DBSCAN
EXPTIME
PSPACE
SCADA
SQUID
UNIVAC I
""".split("\n")

# Dropped by choice rather than by rule. "Algol" the star (Beta Persei) makes an
# identical puzzle to "ALGOL" the language -- the board masks letters, not case,
# so both render as the same five blanks with different answers behind them --
# and the language was preferred. Note this is a one-off call, not a general
# rule: "Acid" and "ACID" collide the same way and both are deliberately kept.
DROPPED = """
Algol
""".split("\n")

# Company builders. Household names, but famous for founding a business rather
# than for any scientific or engineering result. Gordon Moore and Robert Noyce
# co-founded Intel and so belong here by job description, but are kept: Moore's
# law is vocabulary, and Noyce co-invented the integrated circuit alongside Jack
# Kilby, who is in the list.
TECH_FOUNDER = """
Bill Gates
Elon Musk
Jeff Bezos
Larry Page
Mark Zuckerberg
Paul Allen
Satya Nadella
Sergey Brin
Steve Jobs
Steve Wozniak
Sundar Pichai
""".split("\n")

# People whose work is famous under some other name. The test is whether the
# person's name is itself vocabulary a student says out loud -- Doppler, Joule,
# Coulomb, Kekule, Banach, Cayley all survive on that basis, as does anyone
# broadly recognisable. A Nobel alone was not enough; there are far more
# laureates than there are names that turn up in a syllabus.
MINOR_FIGURE = """
Ahmed Zewail
Alain Aspect
Aleksandr Popov (physicist)
Alexander Prokhorov
Allen Newell
Anders Hejlsberg
Annie Jump Cannon
Anton Zeilinger
Arno Allan Penzias
Arthur Ashkin
Barry Barish
Caroline Herschel
Cecilia Payne-Gaposchkin
Donna Strickland
Frances Allen
Gérard Mourou
Harlow Shapley
Hermann Oberth
Igor Kurchatov
James Joseph Sylvester
Jean Bartik
Jill Tarter
John Clauser
Kenneth G. Wilson
Konstantin Novoselov
Larry Wall
Lisa Randall
Marie-Anne Paulze Lavoisier
Niklaus Wirth
Nikolai Vavilov
Nikolay Basov
Percival Lowell
Philip W. Anderson
Pyotr Kapitsa
Rainer Weiss
Rasmus Lerdorf
Robert Burns Woodward
Robert Kahn (computer scientist)
Robert Woodrow Wilson
Seymour Papert
Sheldon Glashow
Shin'ichirō Tomonaga
Tsung-Dao Lee
Vitaly Ginzburg
Vladimir K. Zworykin
Vladimir Vapnik
Walter Brattain
Wilhelm Ostwald
Yukihiro Matsumoto
Zhores Alferov
Élie Metchnikoff
""".split("\n")

# Famous, but not science: internet-culture aphorisms and pure economics that
# rode in on the "named laws" block. Kept apart from OBSCURE because these are
# out of scope rather than too obscure -- their pageviews are all healthy.
OFF_TOPIC = """
Betteridge's law of headlines
Diminishing returns
Econometrics
Economics
Ethnography
Externality
Godwin's law
Goodhart's law
Gross domestic product
Hanlon's razor
Hofstadter's law
Inflation
Network effect
Opportunity cost
Parkinson's Law
Peter principle
Streisand effect
Sturgeon's law
Supply and demand
""".split("\n")

# Specialist terms that belong to one subfield's graduate coursework, plus
# software-implementation trivia no physicist or biologist would meet.
OBSCURE = """
API management
Alcohol oxidation
Antibiotic sensitivity testing
Approximation theory
Array (data type)
Assertion (software development)
Astronomical interferometer
Astronomical naming conventions
Auger electron spectroscopy
Barnsley fern
Best-first search
Bias of an estimator
Bit array
Born approximation
Branching (version control)
Breakpoint
C-symmetry
Carrier generation and recombination
Change-making problem
Charge carrier density
Chemical database
Chemical safety
Classification of discontinuities
Cognitive archaeology
Coin problem
Completeness (order theory)
Concurrency control
Constant (computer programming)
Constraint (mathematics)
Cooling
Dark photon
Decidability (logic)
Decimal representation
Deep inelastic scattering
Dennard scaling
Denotational semantics
Design pattern
Diagnosis
Digit sum
Dilution (equation)
Direct comparison test
Direct proof
Displacement current density
Doubling time
Dropout (neural networks)
Effective field theory
Einstein solid
Ellipsometry
Etching (microfabrication)
Failure analysis
Failure rate
Feature engineering
Feature selection
Fermat primality test
Fermi surface
Fiber laser
Field electron emission
Fixed-point iteration
Frame problem
Free-radical reaction
Giant magnetoresistance
Gunn diode
Hash chain
Hash collision
Heterojunction
Hyperparameter (machine learning)
Inference engine
Information content
Initial value problem
Interpolation search
Ion implantation
Isotope geochemistry
Iterative deepening depth-first search
Johnson's algorithm
Kibble balance
Ladder paradox
Landau levels
Lattice QCD
Learning rate
Ligand field theory
Limit cycle
Linearizability
Load-bearing wall
Loader (computing)
Local search (optimization)
Lock-in amplifier
Logging (computing)
Logical biconditional
Loop invariant
Magnetostratigraphy
Massive compact halo object
Massively parallel sequencing
Mathematical modelling of infectious diseases
Matrix multiplication algorithm
Merge (version control)
Model checking
Molecular-beam epitaxy
Monitor (synchronization)
Monolithic application
Motion planning
Mountain formation
Nanolithography
Neutral current
Neutron activation
Neutron diffraction
Neutron flux
Nodal analysis
Noise (signal processing)
Nonstandard analysis
Nuclear cross section
Number sense
Numerical stability
Ocean exploration
Operational semantics
Optimizing compiler
Page replacement algorithm
Page table
Perfect hash function
Petroleum geology
Photoconductivity
Photodisintegration
Photoemission spectroscopy
Photomultiplier
Poincaré map
Polaron
Polynomial-time reduction
Potential theory
Power transmission
Preprocessor
Present value
Profiling (computer programming)
Program synthesis
Proof by exhaustion
Proton-to-electron mass ratio
Query optimization
Rabin–Karp algorithm
Rate limiting
Readers–writers problem
Recursive definition
Reduction (complexity)
Reference (computer science)
Refining (metallurgy)
Replication (computing)
Retrosynthetic analysis
Rewilding
Root-finding algorithm
Round-off error
Schottky barrier
Science education
Scientific realism
Secondary-ion mass spectrometry
Secret sharing
Seismic base isolation
Semantic network
Semi-empirical mass formula
Servomechanism
Signal averaging
Small-world network
Space complexity
Spectrochemical series
Speculative execution
Spring scale
Sputtering
Stability theory
Steel frame
Stag hunt
Stratigraphy (archaeology)
Strategic dominance
Strategy (game theory)
Suffix array
Suffix tree
Symbol grounding problem
Technological revolution
Termination analysis
Thin film
Tunnel diode
Type-I superconductor
Ultimatum game
Vacuum expectation value
Varicap
Variable and attribute (research)
Variational method (quantum mechanics)
Weak isospin
Weak supervision
Well-founded relation
Wiedemann–Franz law
Wind engineering
Yukawa coupling
Z-buffering
""".split("\n")


def distinct(t):
    return len(set(re.findall(r"[a-z]", t.lower())))


def main():
    src, out = sys.argv[1], sys.argv[2]
    titles = json.load(open(src, encoding="utf-8"))
    obscure = {t.strip() for t in OBSCURE if t.strip()}
    offtopic = {t.strip() for t in OFF_TOPIC if t.strip()}
    latin = {t.strip() for t in LATIN_NAME if t.strip()}
    acronym = {t.strip() for t in ACRONYM_ONLY if t.strip()}
    minor = {t.strip() for t in MINOR_FIGURE if t.strip()}
    founder = {t.strip() for t in TECH_FOUNDER if t.strip()}
    dropped = {t.strip() for t in DROPPED if t.strip()}

    kept, reasons = [], {}
    for t in titles:
        if t.startswith(STRUCTURAL_PREFIX):
            reasons[t] = "roundup page"
        elif distinct(t) < 3:
            reasons[t] = "under 3 letters"
        elif t in offtopic:
            reasons[t] = "not science"
        elif t in latin:
            reasons[t] = "latin name"
        elif t in acronym:
            reasons[t] = "acronym only"
        elif t in dropped:
            reasons[t] = "case twin"
        elif t in founder:
            reasons[t] = "tech founder"
        elif t in minor:
            reasons[t] = "minor figure"
        elif t in obscure:
            reasons[t] = "too specialist"
        else:
            kept.append(t)

    kept.sort(key=str.lower)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(kept, f, ensure_ascii=False, indent=4)
        f.write("\n")

    json.dump(reasons, open(sys.argv[3], "w", encoding="utf-8"), ensure_ascii=False)
    unmatched = (obscure | offtopic | latin | acronym | minor | founder | dropped) - set(reasons)
    print(f"kept {len(kept)} of {len(titles)}; removed {len(reasons)}")
    for k in ("roundup page", "under 3 letters", "not science", "latin name",
              "acronym only", "case twin", "tech founder", "minor figure",
              "too specialist"):
        print(f"  {k}: {sum(1 for v in reasons.values() if v == k)}")
    if unmatched:
        print(f"  WARNING {len(unmatched)} cut entries matched nothing:")
        for u in sorted(unmatched):
            print(f"    {u}")


if __name__ == "__main__":
    main()
