-- ============================================================================
-- test_data.sql — Synthetic test data for Medicilon CRO Intelligence Platform
-- Generates 100+ LinkedIn posts + funding rounds for AI Scoring & Tiering tests
-- Usage: sqlite3 data/platform.db < test_data.sql
-- ============================================================================

-- ═══ LINKEDIN POSTS (80 synthetic posts) ═══════════════════════════════════

-- High-priority (score 70-100): CRO outsourcing signals, decision-makers
INSERT OR IGNORE INTO linkedin_posts (source_id, post_url, author_name, author_title, author_company, content, post_date, relevance_score, matched_keywords, processed)
VALUES
('synth-001', 'https://linkedin.com/posts/1', 'Sarah Chen', 'VP Research & Development', 'Nexus Therapeutics',
 'Excited to announce that Nexus Therapeutics is seeking CRO partners for our upcoming Phase 2 oncology program. We need comprehensive DMPK, toxicology, and bioanalysis support for our lead ADC candidate. RFPs going out next week — reach out if interested in partnering!',
 '2026-05-20T14:30:00Z', 85, 'CRO, DMPK, toxicology, bioanalysis, ADC, oncology, Phase 2, RFP, partnering', 1);

INSERT OR IGNORE INTO linkedin_posts (source_id, post_url, author_name, author_title, author_company, content, post_date, relevance_score, matched_keywords, processed)
VALUES
('synth-002', 'https://linkedin.com/posts/2', 'Michael Torres', 'CSO', 'ProtaGene Therapeutics',
 'We just closed our $95M Series B led by Deerfield and Novo Holdings! 🎉 This funding will accelerate our protein therapeutics pipeline. We are evaluating CRO partners for GMP-compliant bioanalysis and IND-enabling toxicology studies. If your CRO has biologics characterization capabilities, let us know!',
 '2026-05-18T09:15:00Z', 92, 'CRO, bioanalysis, toxicology, IND, biologics, GMP, protein, Series B, funding', 1);

INSERT OR IGNORE INTO linkedin_posts (source_id, post_url, author_name, author_title, author_company, content, post_date, relevance_score, matched_keywords, processed)
VALUES
('synth-003', 'https://linkedin.com/posts/3', 'Jennifer Park', 'Head of Preclinical Development', 'CellVantage Therapeutics',
 'Looking for a CRO with strong cell therapy experience. We need in vivo efficacy models, PK/PD profiling, and GLP toxicology for our CAR-T program heading toward IND. Prefer East Coast or China-based CROs with dual filing experience.',
 '2026-05-17T11:00:00Z', 90, 'CRO, in vivo, efficacy, GLP, toxicology, IND, cell therapy, preclinical', 1);

INSERT OR IGNORE INTO linkedin_posts (source_id, post_url, author_name, author_title, author_company, content, post_date, relevance_score, matched_keywords, processed)
VALUES
('synth-004', 'https://linkedin.com/posts/4', 'David Kim', 'Director of Toxicology', 'Repertoire Immune Medicines',
 'Repertoire is advancing 3 programs to IND in 2026. We need a strategic CRO partnership covering DMPK, safety pharmacology, and GLP toxicology across multiple modalities (small molecule, antibody, and mRNA). Long-term partnership preferred over transactional work.',
 '2026-05-15T15:45:00Z', 88, 'CRO, DMPK, toxicology, IND, GLP, antibody, small molecule, mRNA, pharmacology', 1);

INSERT OR IGNORE INTO linkedin_posts (source_id, post_url, author_name, author_title, author_company, content, post_date, relevance_score, matched_keywords, processed)
VALUES
('synth-005', 'https://linkedin.com/posts/5', 'Rachel Gupta', 'SVP Discovery', 'Adlai Nortye Biopharma',
 'Successful IPO on NASDAQ! 🚀 Now scaling our preclinical operations. We need CRO support for: oncology mouse models, DMPK for CNS-penetrant small molecules, and bioanalytical method development for LC-MS/MS. Budget available for Q3 2026 start.',
 '2026-05-14T08:00:00Z', 86, 'CRO, DMPK, mouse model, preclinical, oncology, small molecule, IPO, bioanalytical', 1);

INSERT OR IGNORE INTO linkedin_posts (source_id, post_url, author_name, author_title, author_company, content, post_date, relevance_score, matched_keywords, processed)
VALUES
('synth-006', 'https://linkedin.com/posts/6', 'Thomas Wright', 'VP Chemistry', 'Aureka Biotech',
 'Our PROTAC program is advancing rapidly. We are outsourcing formulation development and CMC analytical support. Looking for a CDMO/CRO with experience in PROTAC degrader molecules for solid oral dosage form development.',
 '2026-05-13T10:30:00Z', 78, 'CRO, CDMO, CMC, formulation, PROTAC, outsourcing', 1);

INSERT OR IGNORE INTO linkedin_posts (source_id, post_url, author_name, author_title, author_company, content, post_date, relevance_score, matched_keywords, processed)
VALUES
('synth-007', 'https://linkedin.com/posts/7', 'Anna Lindström', 'CEO', 'Nordic BioAnalytics',
 'Nordic BioAnalytics has been acquired by a PE consortium. We are now expanding our bioanalytical capabilities across Europe and looking for strategic partners. Interesting times ahead!',
 '2026-05-12T12:00:00Z', 72, 'CRO, bioanalysis, investment, partnership, strategic partner', 1);

INSERT OR IGNORE INTO linkedin_posts (source_id, post_url, author_name, author_title, author_company, content, post_date, relevance_score, matched_keywords, processed)
VALUES
('synth-008', 'https://linkedin.com/posts/8', 'Robert Chang', 'Head of Outsourcing', 'GenEdit Therapeutics',
 'RFP Alert: GenEdit is seeking CRO partners for GLP tox and biodistribution studies on our lead CRISPR-based gene therapy program. Pre-IND meeting scheduled for Q4 2026. Experience with AAV vectors and NGS-based biodistribution required.',
 '2026-05-11T09:45:00Z', 95, 'CRO, RFP, GLP, gene therapy, IND, tox, outsourcing, NGS', 1);

INSERT OR IGNORE INTO linkedin_posts (source_id, post_url, author_name, author_title, author_company, content, post_date, relevance_score, matched_keywords, processed)
VALUES
('synth-009', 'https://linkedin.com/posts/9', 'Lisa Park', 'Director CMC', 'ImmunoCore Biologics',
 'Seeking CDMO partner for phase-appropriate CMC development of our bispecific antibody program. Need cell line development, upstream/downstream process development, and analytical characterization. Late-phase readiness is key.',
 '2026-05-10T14:00:00Z', 76, 'CRO, CDMO, CMC, antibody, biologics, analytical', 1);

INSERT OR IGNORE INTO linkedin_posts (source_id, post_url, author_name, author_title, author_company, content, post_date, relevance_score, matched_keywords, processed)
VALUES
('synth-010', 'https://linkedin.com/posts/10', 'Kevin Zhao', 'VP Pharmacology', 'Atlas Venture portfolio company',
 'Our stealth-mode biotech just raised $50M seed. Building out our preclinical team and need a trusted CRO for: in vivo pharmacology, PK/PD modeling, and biomarker analysis. DM me for details!',
 '2026-05-09T16:20:00Z', 82, 'CRO, in vivo, pharmacology, PK, biomarker, seed, investment, preclinical', 1);

-- Medium priority (score 40-69): biotech news, hiring, partnership discussions
INSERT OR IGNORE INTO linkedin_posts (source_id, post_url, author_name, author_title, author_company, content, post_date, relevance_score, matched_keywords, processed)
VALUES
('synth-011', 'https://linkedin.com/posts/11', 'Maria Rodriguez', 'Research Scientist', 'Pfizer',
 'Presenting our latest DMPK findings at the ISSX meeting next month. Exciting data on a novel prodrug approach for CNS delivery. Stop by Poster #342!',
 '2026-05-19T11:00:00Z', 55, 'DMPK, drug discovery, CNS, research', 1);

INSERT OR IGNORE INTO linkedin_posts (source_id, post_url, author_name, author_title, author_company, content, post_date, relevance_score, matched_keywords, processed)
VALUES
('synth-012', 'https://linkedin.com/posts/12', 'James Liu', 'Clinical Research Associate', 'Merck',
 'Looking forward to attending BIO 2026 in Boston. Anyone else going? Would love to connect and discuss clinical development strategies.',
 '2026-05-18T13:00:00Z', 42, 'clinical, drug development', 1);

INSERT OR IGNORE INTO linkedin_posts (source_id, post_url, author_name, author_title, author_company, content, post_date, relevance_score, matched_keywords, processed)
VALUES
('synth-013', 'https://linkedin.com/posts/13', 'Emily Watson', 'Senior Director Biologics', 'AstraZeneca',
 'Great collaboration with our CDMO partners on scaling up our bispecific antibody manufacturing. Process development is key to successful tech transfer.',
 '2026-05-16T09:30:00Z', 56, 'CDMO, biologics, antibody, manufacturing, collaboration', 1);

INSERT OR IGNORE INTO linkedin_posts (source_id, post_url, author_name, author_title, author_company, content, post_date, relevance_score, matched_keywords, processed)
VALUES
('synth-014', 'https://linkedin.com/posts/14', 'Carlos Mendez', 'Head of Bioinformatics', 'Moderna',
 'Exciting progress on our mRNA platform! New lipid nanoparticle formulations showing improved tissue targeting in preclinical models. mRNA therapeutics are the future.',
 '2026-05-15T10:00:00Z', 48, 'mRNA, preclinical, drug discovery, formulation', 1);

INSERT OR IGNORE INTO linkedin_posts (source_id, post_url, author_name, author_title, author_company, content, post_date, relevance_score, matched_keywords, processed)
VALUES
('synth-015', 'https://linkedin.com/posts/15', 'Priya Sharma', 'VP Clinical Operations', 'Gilead Sciences',
 'Our Phase 3 readout is coming up — keeping fingers crossed! This has been a massive effort across 15 countries with incredible CRO support. Shoutout to our clinical partners!',
 '2026-05-14T14:00:00Z', 52, 'CRO, Phase 3, clinical, clinical trial, partner', 1);

INSERT OR IGNORE INTO linkedin_posts (source_id, post_url, author_name, author_title, author_company, content, post_date, relevance_score, matched_keywords, processed)
VALUES
('synth-016', 'https://linkedin.com/posts/16', 'Alex Turner', 'Drug Metabolism Scientist', 'Genentech',
 'Interesting paper on transporter-mediated DDI risk assessment using PBPK modeling. Essential reading for DMPK scientists working on NDA submissions.',
 '2026-05-13T08:00:00Z', 45, 'DMPK, drug metabolism, NDA', 1);

INSERT OR IGNORE INTO linkedin_posts (source_id, post_url, author_name, author_title, author_company, content, post_date, relevance_score, matched_keywords, processed)
VALUES
('synth-017', 'https://linkedin.com/posts/17', 'Grace OHara', 'Associate Director', 'Regeneron',
 'We are hiring! Multiple positions open in preclinical development. Looking for talented scientists with expertise in pharmacokinetics, immunogenicity assessment, and bioanalysis. Apply on our careers page.',
 '2026-05-12T12:30:00Z', 44, 'preclinical, pharmacokinetics, bioanalysis, drug development', 1);

INSERT OR IGNORE INTO linkedin_posts (source_id, post_url, author_name, author_title, author_company, content, post_date, relevance_score, matched_keywords, processed)
VALUES
('synth-018', 'https://linkedin.com/posts/18', 'Daniel Fischer', 'CRO Alliance Manager', 'Novartis',
 'Building our preferred CRO network for 2027-2029. Looking to expand in Asia-Pacific region. Areas of interest: bioanalysis, safety assessment, and biomarker development. DM if interested.',
 '2026-05-11T16:00:00Z', 65, 'CRO, bioanalysis, safety assessment, biomarker, drug development', 1);

INSERT OR IGNORE INTO linkedin_posts (source_id, post_url, author_name, author_title, author_company, content, post_date, relevance_score, matched_keywords, processed)
VALUES
('synth-019', 'https://linkedin.com/posts/19', 'Sophie Laurent', 'Senior Scientist', 'Sanofi',
 'Just wrapped up a successful tox study comparing two lead candidates. Clear winner identified! Moving into IND-enabling studies next. Great teamwork from everyone involved.',
 '2026-05-10T09:00:00Z', 48, 'tox, IND, preclinical, toxicology', 1);

INSERT OR IGNORE INTO linkedin_posts (source_id, post_url, author_name, author_title, author_company, content, post_date, relevance_score, matched_keywords, processed)
VALUES
('synth-020', 'https://linkedin.com/posts/20', 'Omar Hassan', 'VP Business Development', 'WuXi AppTec',
 'WuXi AppTec expands DMPK and bioanalytical services at our New Jersey site. New capacity for large-molecule bioanalysis and immunogenicity testing. Reach out to learn more!',
 '2026-05-09T14:00:00Z', 60, 'CRO, DMPK, bioanalysis, biologics, drug development', 1);

-- More synthetic posts — biotech ecosystem signals
INSERT OR IGNORE INTO linkedin_posts (source_id, post_url, author_name, author_title, author_company, content, post_date, relevance_score, matched_keywords, processed)
VALUES
('synth-021', 'https://linkedin.com/posts/21', 'Nicole Brooks', 'Director of Biology', 'Beam Therapeutics',
 'Our base editing platform is making tremendous progress in hematology indications. We are exploring CRO partners for IND-enabling tox studies. Looking for GLP-compliant labs with gene editing experience.',
 '2026-05-08T10:00:00Z', 75, 'CRO, IND, tox, gene therapy, GLP, preclinical', 1);

INSERT OR IGNORE INTO linkedin_posts (source_id, post_url, author_name, author_title, author_company, content, post_date, relevance_score, matched_keywords, processed)
VALUES
('synth-022', 'https://linkedin.com/posts/22', 'William Park', 'CEO', 'Vertex Pharmaceuticals',
 'Vertex announces positive Phase 3 results for our next-generation CFTR modulator. This milestone represents years of dedication from our team and partners. Preparing NDA submission for 2027.',
 '2026-05-07T08:30:00Z', 38, 'Phase 3, NDA, drug development, clinical trial', 1);

INSERT OR IGNORE INTO linkedin_posts (source_id, post_url, author_name, author_title, author_company, content, post_date, relevance_score, matched_keywords, processed)
VALUES
('synth-023', 'https://linkedin.com/posts/23', 'Hannah Chen', 'Head of Bioanalysis', 'EQRx',
 'Building our bioanalytical strategy for multiple programs. Evaluating CROs with high-throughput LC-MS/MS capabilities and regulatory bioanalysis experience. Interested in long-term FTE-based partnerships.',
 '2026-05-06T15:00:00Z', 70, 'CRO, bioanalysis, LC-MS, regulatory, partner', 1);

INSERT OR IGNORE INTO linkedin_posts (source_id, post_url, author_name, author_title, author_company, content, post_date, relevance_score, matched_keywords, processed)
VALUES
('synth-024', 'https://linkedin.com/posts/24', 'Sebastian Mueller', 'VP Drug Safety', 'BioNTech',
 'Drug safety is paramount. Our team is expanding its pharmacovigilance and nonclinical safety capabilities. Looking to partner with experienced CROs for comprehensive toxicology programs.',
 '2026-05-05T11:00:00Z', 62, 'CRO, toxicology, safety assessment, drug development, partner', 1);

INSERT OR IGNORE INTO linkedin_posts (source_id, post_url, author_name, author_title, author_company, content, post_date, relevance_score, matched_keywords, processed)
VALUES
('synth-025', 'https://linkedin.com/posts/25', 'Yuki Tanaka', 'Pharmacology Lead', 'Takeda',
 'Our GI pharmacology team is expanding into novel modalities. Looking for CROs with expertise in organoid models and advanced in vivo pharmacology platforms for IBD research.',
 '2026-05-04T09:00:00Z', 58, 'CRO, in vivo, pharmacology, drug discovery', 1);

INSERT OR IGNORE INTO linkedin_posts (source_id, post_url, author_name, author_title, author_company, content, post_date, relevance_score, matched_keywords, processed)
VALUES
('synth-026', 'https://linkedin.com/posts/26', 'Amanda Foster', 'Principal Scientist', 'AbbVie',
 'New publication alert: Our team developed a novel PBPK model for predicting human PK of antibody-drug conjugates. Check it out in Drug Metabolism and Disposition!',
 '2026-05-03T12:00:00Z', 40, 'DMPK, ADC, antibody, drug metabolism, PK', 1);

INSERT OR IGNORE INTO linkedin_posts (source_id, post_url, author_name, author_title, author_company, content, post_date, relevance_score, matched_keywords, processed)
VALUES
('synth-027', 'https://linkedin.com/posts/27', 'Raj Patel', 'Head of DMPK', 'Kura Oncology',
 'Our DMPK team is seeking a CRO partner for definitive ADME studies using radiolabeled compound. Need quantitative whole-body autoradiography and metabolite profiling capabilities. Please DM me!',
 '2026-05-02T14:00:00Z', 80, 'CRO, DMPK, ADME, drug metabolism, partner', 1);

INSERT OR IGNORE INTO linkedin_posts (source_id, post_url, author_name, author_title, author_company, content, post_date, relevance_score, matched_keywords, processed)
VALUES
('synth-028', 'https://linkedin.com/posts/28', 'Catherine Mills', 'Clinical Development Director', 'Eli Lilly',
 'Lilly''s obesity pipeline is advancing rapidly. Our tirzepatide successor program is entering Phase 2 with strong preclinical data. Exciting time for metabolic disease research!',
 '2026-05-01T10:00:00Z', 35, 'Phase 2, clinical trial, preclinical, drug development', 1);

INSERT OR IGNORE INTO linkedin_posts (source_id, post_url, author_name, author_title, author_company, content, post_date, relevance_score, matched_keywords, processed)
VALUES
('synth-029', 'https://linkedin.com/posts/29', 'Jason Wu', 'CEO', 'Enlaza Therapeutics',
 'Enlaza Therapeutics raises $120M Series C to advance covalent biologics platform! We are now building out our CMC and preclinical teams. Reach out if you want to be part of this journey.',
 '2026-04-30T08:00:00Z', 68, 'CRO, CMC, preclinical, Series C, funding, biologics, investment', 1);

INSERT OR IGNORE INTO linkedin_posts (source_id, post_url, author_name, author_title, author_company, content, post_date, relevance_score, matched_keywords, processed)
VALUES
('synth-030', 'https://linkedin.com/posts/30', 'Mia Johansson', 'Director of Outsourcing', 'ORIC Pharmaceuticals',
 'Managing our CRO relationships for two clinical-stage programs. Looking to expand our preferred provider network for bioanalytical and DMPK support. Interested CROs, please reach out with capabilities presentations.',
 '2026-04-29T13:00:00Z', 68, 'CRO, DMPK, bioanalysis, outsourcing, clinical', 1);

INSERT OR IGNORE INTO linkedin_posts (source_id, post_url, author_name, author_title, author_company, content, post_date, relevance_score, matched_keywords, processed)
VALUES
('synth-031', 'https://linkedin.com/posts/31', 'Chris Henderson', 'VP Manufacturing', 'Arcellx',
 'Our GMP manufacturing facility for cell therapies is online! Now looking for analytical CRO partners to support lot release and stability testing. cGMP-compliant bioassay development needed.',
 '2026-04-28T11:30:00Z', 65, 'CRO, GMP, cell therapy, analytical, manufacturing, partner', 1);

INSERT OR IGNORE INTO linkedin_posts (source_id, post_url, author_name, author_title, author_company, content, post_date, relevance_score, matched_keywords, processed)
VALUES
('synth-032', 'https://linkedin.com/posts/32', 'Linda Zhou', 'Toxicology Director', 'Blueprint Medicines',
 'Completed our 6-month GLP tox program for BLU-945 successor — clean tox profile! Great work by our CRO partner on this program. Ready for IND filing.',
 '2026-04-27T15:00:00Z', 55, 'CRO, GLP, tox, IND, toxicology, partner', 1);

INSERT OR IGNORE INTO linkedin_posts (source_id, post_url, author_name, author_title, author_company, content, post_date, relevance_score, matched_keywords, processed)
VALUES
('synth-033', 'https://linkedin.com/posts/33', 'Peter Novak', 'VP Research', 'Dewpoint Therapeutics',
 'Condensate biology is unlocking undruggable targets! Our team is growing and we need CRO support for high-content screening and advanced cellular pharmacology. Exciting science ahead!',
 '2026-04-26T09:00:00Z', 52, 'CRO, drug discovery, pharmacology', 1);

INSERT OR IGNORE INTO linkedin_posts (source_id, post_url, author_name, author_title, author_company, content, post_date, relevance_score, matched_keywords, processed)
VALUES
('synth-034', 'https://linkedin.com/posts/34', 'Fatima Al-Rashid', 'Clinical Pharmacology Lead', 'Bristol-Myers Squibb',
 'Presenting our clinical pharmacology strategy for a first-in-class immunology asset. Integrated PK/PD modeling was key to dose selection for Phase 2. Collaboration with quantitative pharmacology experts made this possible.',
 '2026-04-25T14:00:00Z', 38, 'PK, Phase 2, clinical, pharmacology, DMPK', 1);

INSERT OR IGNORE INTO linkedin_posts (source_id, post_url, author_name, author_title, author_company, content, post_date, relevance_score, matched_keywords, processed)
VALUES
('synth-035', 'https://linkedin.com/posts/35', 'Andrew Kim', 'Sr. Director Discovery', 'Relay Therapeutics',
 'Our Dynamo platform is generating exciting small molecule candidates against previously undruggable targets. Expanding our preclinical team — need CRO partners for in vivo efficacy and PK studies.',
 '2026-04-24T10:00:00Z', 62, 'CRO, in vivo, PK, preclinical, small molecule, drug discovery, efficacy', 1);

INSERT OR IGNORE INTO linkedin_posts (source_id, post_url, author_name, author_title, author_company, content, post_date, relevance_score, matched_keywords, processed)
VALUES
('synth-036', 'https://linkedin.com/posts/36', 'Diana Torres', 'Head of Regulatory', 'Intellia Therapeutics',
 'Intellia''s first in vivo CRISPR therapy advancing toward IND! Our regulatory team is working closely with CRO partners to compile the nonclinical package. GLP bioanalytical and biodistribution data coming together nicely.',
 '2026-04-23T12:00:00Z', 58, 'CRO, IND, GLP, gene therapy, bioanalysis, partner', 1);

INSERT OR IGNORE INTO linkedin_posts (source_id, post_url, author_name, author_title, author_company, content, post_date, relevance_score, matched_keywords, processed)
VALUES
('synth-037', 'https://linkedin.com/posts/37', 'Naveen Krishnan', 'CMC Project Manager', 'FogPharma',
 'Helicon therapeutics are a new modality — and CMC is challenging! Looking for analytical CROs with experience in characterizing constrained peptide macrocycles. Novel analytical methods needed.',
 '2026-04-22T08:00:00Z', 60, 'CRO, CMC, peptide, analytical, drug development', 1);

INSERT OR IGNORE INTO linkedin_posts (source_id, post_url, author_name, author_title, author_company, content, post_date, relevance_score, matched_keywords, processed)
VALUES
('synth-038', 'https://linkedin.com/posts/38', 'Tanya Williams', 'Associate Director Bioanalysis', 'Agios Pharmaceuticals',
 'Seeking CRO partner for validating a PK assay for our rare disease program. Need LC-MS/MS-based method with LLOQ in pg/mL range for plasma and CSF matrices. DM for details.',
 '2026-04-21T15:30:00Z', 72, 'CRO, DMPK, PK, bioanalysis, LC-MS, rare disease, partner', 1);

INSERT OR IGNORE INTO linkedin_posts (source_id, post_url, author_name, author_title, author_company, content, post_date, relevance_score, matched_keywords, processed)
VALUES
('synth-039', 'https://linkedin.com/posts/39', 'Marcus Lee', 'CEO', 'Totus Medicines',
 'Totus Medicines closes $85M Series B to advance covalent small molecule pipeline. We are now actively selecting CRO partners for IND-enabling studies across multiple programs. Serious inquiries only.',
 '2026-04-20T09:00:00Z', 82, 'CRO, IND, small molecule, Series B, funding, investment, preclinical', 1);

INSERT OR IGNORE INTO linkedin_posts (source_id, post_url, author_name, author_title, author_company, content, post_date, relevance_score, matched_keywords, processed)
VALUES
('synth-040', 'https://linkedin.com/posts/40', 'Vanessa Moore', 'Drug Discovery Scientist', 'Amgen',
 'Amgen''s multispecific antibody platform is delivering incredible results. Our tri-specific T-cell engagers show potent tumor killing with reduced cytokine release. Check out our latest publication in Nature Biotechnology!',
 '2026-04-19T11:00:00Z', 30, 'antibody, biologic, drug discovery', 1);

-- Lower priority (score 15-39): general industry content
INSERT OR IGNORE INTO linkedin_posts (source_id, post_url, author_name, author_title, author_company, content, post_date, relevance_score, matched_keywords, processed)
VALUES
('synth-041', 'https://linkedin.com/posts/41', 'Tom Bradley', 'Business Development', 'Labcorp Drug Development',
 'Labcorp expands central laboratory services across Asia-Pacific. New facilities in Shanghai and Singapore will support growing clinical trial demand in the region.',
 '2026-05-19T08:00:00Z', 25, 'clinical trial, CRO', 1);

INSERT OR IGNORE INTO linkedin_posts (source_id, post_url, author_name, author_title, author_company, content, post_date, relevance_score, matched_keywords, processed)
VALUES
('synth-042', 'https://linkedin.com/posts/42', 'Rebecca Sloan', 'Clinical Operations', 'IQVIA',
 'Interesting analysis from IQVIA: Global clinical trial starts up 12% YoY in Q1 2026 — driven by oncology, immunology, and rare disease. Great outlook for the CRO industry!',
 '2026-05-18T10:00:00Z', 20, 'clinical trial, CRO, oncology', 1);

INSERT OR IGNORE INTO linkedin_posts (source_id, post_url, author_name, author_title, author_company, content, post_date, relevance_score, matched_keywords, processed)
VALUES
('synth-043', 'https://linkedin.com/posts/43', 'Mark Fisher', 'Investor', 'OrbiMed Advisors',
 'Healthcare VC funding in Q1 2026: $18.2B across 340 deals. Biotech leads with $9.8B, followed by healthtech and medical devices. Strong start to the year for life sciences investment.',
 '2026-05-17T07:00:00Z', 28, 'biotech, investment, funding, venture', 1);

INSERT OR IGNORE INTO linkedin_posts (source_id, post_url, author_name, author_title, author_company, content, post_date, relevance_score, matched_keywords, processed)
VALUES
('synth-044', 'https://linkedin.com/posts/44', 'Julia Chen', 'Research Fellow', 'NIH',
 'Exciting developments in gene therapy delivery: new AAV capsids show 10x improved CNS transduction in non-human primates. Published today in Science Translational Medicine.',
 '2026-05-16T12:00:00Z', 22, 'gene therapy, drug discovery, preclinical', 1);

INSERT OR IGNORE INTO linkedin_posts (source_id, post_url, author_name, author_title, author_company, content, post_date, relevance_score, matched_keywords, processed)
VALUES
('synth-045', 'https://linkedin.com/posts/45', 'Ryan Cooper', 'Clinical Scientist', 'Roche',
 'Roche''s personalized healthcare strategy is transforming drug development. Integrating genomics, real-world data, and digital biomarkers to identify the right patients for the right treatments.',
 '2026-05-15T09:00:00Z', 18, 'drug development, biomarker', 1);

INSERT OR IGNORE INTO linkedin_posts (source_id, post_url, author_name, author_title, author_company, content, post_date, relevance_score, matched_keywords, processed)
VALUES
('synth-046', 'https://linkedin.com/posts/46', 'Kate Morrison', 'Regulatory Affairs', 'FDA',
 'FDA publishes new guidance on cell and gene therapy manufacturing — emphasis on process validation and potency assay development. Important reading for anyone in the CMC space.',
 '2026-05-14T14:00:00Z', 20, 'FDA, CMC, gene therapy, cell therapy, manufacturing', 1);

INSERT OR IGNORE INTO linkedin_posts (source_id, post_url, author_name, author_title, author_company, content, post_date, relevance_score, matched_keywords, processed)
VALUES
('synth-047', 'https://linkedin.com/posts/47', 'Brian Mitchell', 'VP Sales', 'Charles River Laboratories',
 'Charles River announces acquisition of AI-driven toxicology prediction platform. Enhancing our safety assessment capabilities with machine learning — reducing time to IND for our biotech partners.',
 '2026-05-13T10:00:00Z', 32, 'CRO, toxicology, IND, safety assessment, partner, acquisition', 1);

INSERT OR IGNORE INTO linkedin_posts (source_id, post_url, author_name, author_title, author_company, content, post_date, relevance_score, matched_keywords, processed)
VALUES
('synth-048', 'https://linkedin.com/posts/48', 'Samantha Wright', 'Biostatistician', 'Parexel',
 'Adaptive trial designs are gaining traction in oncology. Our latest whitepaper explores Bayesian approaches for dose-finding in Phase 1 oncology trials. Link in comments!',
 '2026-05-12T08:00:00Z', 18, 'Phase 1, clinical trial, oncology', 1);

INSERT OR IGNORE INTO linkedin_posts (source_id, post_url, author_name, author_title, author_company, content, post_date, relevance_score, matched_keywords, processed)
VALUES
('synth-049', 'https://linkedin.com/posts/49', 'Ahmed Syed', 'Medicinal Chemist', 'Alnylam Pharmaceuticals',
 'RNAi therapeutics continue to deliver! Our latest program targeting a liver-expressed gene shows 95% knockdown with quarterly dosing. Transformative potential for patients.',
 '2026-05-11T13:00:00Z', 20, 'RNA, therapeutic, drug discovery', 1);

INSERT OR IGNORE INTO linkedin_posts (source_id, post_url, author_name, author_title, author_company, content, post_date, relevance_score, matched_keywords, processed)
VALUES
('synth-050', 'https://linkedin.com/posts/50', 'Joshua Green', 'Patent Attorney', 'Wilson Sonsini',
 'Biotech patent landscape 2026: PROTACs, ADCs, and bispecific antibodies dominate new filings. Cell and gene therapy patents growing at 22% CAGR. Interesting trends in CRISPR IP.',
 '2026-05-10T16:00:00Z', 22, 'biotech, ADC, antibody, PROTAC, gene therapy, CRISPR', 1);

-- More high-priority posts with specific CRO needs
INSERT OR IGNORE INTO linkedin_posts (source_id, post_url, author_name, author_title, author_company, content, post_date, relevance_score, matched_keywords, processed)
VALUES
('synth-051', 'https://linkedin.com/posts/51', 'Michelle Carter', 'Director of Preclinical', 'Magnet Biomedicine',
 'We are building our preclinical development strategy and seeking a CRO with strong in vivo pharmacology capabilities in immunology. Our lead program targets autoimmune disease with a novel mechanism. Need expertise in: mouse models of RA, PK/PD, cytokine profiling, and histopathology.',
 '2026-04-18T14:00:00Z', 82, 'CRO, in vivo, pharmacology, PK, preclinical, immunology, autoimmune, mouse model', 1);

INSERT OR IGNORE INTO linkedin_posts (source_id, post_url, author_name, author_title, author_company, content, post_date, relevance_score, matched_keywords, processed)
VALUES
('synth-052', 'https://linkedin.com/posts/52', 'Ryan Nakamura', 'Head of CMC Strategy', 'Kymera Therapeutics',
 'PROTAC degraders require unique CMC considerations. Looking for a CDMO with experience in amorphous solid dispersions and challenging small molecule formulations. Our lead program is entering IND-enabling phase.',
 '2026-04-17T11:00:00Z', 75, 'CRO, CDMO, CMC, PROTAC, IND, small molecule, formulation', 1);

INSERT OR IGNORE INTO linkedin_posts (source_id, post_url, author_name, author_title, author_company, content, post_date, relevance_score, matched_keywords, processed)
VALUES
('synth-053', 'https://linkedin.com/posts/53', 'Helena Bergström', 'VP Translational Medicine', 'Werewolf Therapeutics',
 'Werewolf''s conditionally activated cytokines are showing remarkable tumor-localized activity. We are now seeking CRO partners for IND-enabling tox and PK/PD studies. Must have experience with bispecific and cytokine therapeutics.',
 '2026-04-16T09:00:00Z', 78, 'CRO, IND, tox, PK, preclinical, biologic, partner', 1);

INSERT OR IGNORE INTO linkedin_posts (source_id, post_url, author_name, author_title, author_company, content, post_date, relevance_score, matched_keywords, processed)
VALUES
('synth-054', 'https://linkedin.com/posts/54', 'Paul Andersen', 'CEO', 'Apogee Therapeutics',
 'Apogee closes $150M Series C! We are now scaling our inflammatory disease pipeline. Actively selecting CRO partners for GLP tox, bioanalysis, and clinical sample management. Fast-growing team — 50+ hires planned in 2026!',
 '2026-04-15T08:00:00Z', 85, 'CRO, GLP, tox, bioanalysis, Series C, funding, investment, clinical', 1);

INSERT OR IGNORE INTO linkedin_posts (source_id, post_url, author_name, author_title, author_company, content, post_date, relevance_score, matched_keywords, processed)
VALUES
('synth-055', 'https://linkedin.com/posts/55', 'Sophie Martin', 'Bioanalytical Lead', 'C4 Therapeutics',
 'Developing bioanalytical methods for targeted protein degraders is challenging but rewarding. Our team is looking for a CRO lab with expertise in quantitative proteomics and targeted MS assays. Let me know if you have recommendations!',
 '2026-04-14T12:00:00Z', 62, 'CRO, bioanalysis, bioanalytical, drug development', 1);

INSERT OR IGNORE INTO linkedin_posts (source_id, post_url, author_name, author_title, author_company, content, post_date, relevance_score, matched_keywords, processed)
VALUES
('synth-056', 'https://linkedin.com/posts/56', 'Daniel Ortega', 'VP Clinical Pharmacology', 'Arvinas',
 'Our PROTAC platform is delivering in the clinic! Seeking CRO partners for clinical DMPK support — human ADME study design, metabolite profiling, and drug-drug interaction assessment. Multi-year program with significant budget.',
 '2026-04-13T15:00:00Z', 80, 'CRO, DMPK, ADME, clinical, PROTAC, drug metabolism, partner', 1);

INSERT OR IGNORE INTO linkedin_posts (source_id, post_url, author_name, author_title, author_company, content, post_date, relevance_score, matched_keywords, processed)
VALUES
('synth-057', 'https://linkedin.com/posts/57', 'Rachel Lee', 'Director of Operations', 'Seismic Therapeutic',
 'Our machine learning-powered immunology platform is generating exciting leads. We are vetting CRO partners for integrated discovery services including protein engineering, in vitro pharmacology, and PK screening. Fast turnaround preferred.',
 '2026-04-12T10:00:00Z', 55, 'CRO, PK, pharmacology, drug discovery, partner', 1);

INSERT OR IGNORE INTO linkedin_posts (source_id, post_url, author_name, author_title, author_company, content, post_date, relevance_score, matched_keywords, processed)
VALUES
('synth-058', 'https://linkedin.com/posts/58', 'Oliver Schmidt', 'Head of Toxicology', 'Bayer Pharmaceuticals',
 'Presenting at the Society of Toxicology annual meeting next week. Our talk covers novel in vitro models for predicting DILI risk. Great progress in reducing animal studies while maintaining safety standards.',
 '2026-04-11T08:30:00Z', 42, 'toxicology, drug metabolism, in vivo, safety assessment', 1);

INSERT OR IGNORE INTO linkedin_posts (source_id, post_url, author_name, author_title, author_company, content, post_date, relevance_score, matched_keywords, processed)
VALUES
('synth-059', 'https://linkedin.com/posts/59', 'Cynthia Zhao', 'SVP Preclinical', 'Janux Therapeutics',
 'Our tumor-activated T cell engagers are advancing toward the clinic! We need a CRO that can handle complex multi-arm PK/PD studies with immunocompetent mouse models. Experience with humanized mouse models is a plus.',
 '2026-04-10T14:30:00Z', 72, 'CRO, PK, preclinical, in vivo, mouse model, Phase 1', 1);

INSERT OR IGNORE INTO linkedin_posts (source_id, post_url, author_name, author_title, author_company, content, post_date, relevance_score, matched_keywords, processed)
VALUES
('synth-060', 'https://linkedin.com/posts/60', 'Brandon Hayes', 'CEO', 'Odyssey Therapeutics',
 'Odyssey raises $215M Series C led by Fidelity! We are expanding our precision immunology pipeline with 4 programs entering IND-enabling studies. Now building our preclinical CRO network. Interested CROs — please reach out.',
 '2026-04-09T08:00:00Z', 90, 'CRO, IND, preclinical, Series C, funding, investment, immunology', 1);

-- ===========================================================================
-- ═══ LINKEDIN CONTACTS (40 decision-makers) ════════════════════════════
-- ===========================================================================

INSERT OR IGNORE INTO linkedin_contacts (source_id, name, title, company, company_state, linkedin_url, connection_degree, relevance_score)
VALUES
('contact-001', 'Sarah Chen', 'VP Research & Development', 'Nexus Therapeutics', 'MA', 'https://linkedin.com/in/sarahchen', '2nd', 9.2);
INSERT OR IGNORE INTO linkedin_contacts (source_id, name, title, company, company_state, linkedin_url, connection_degree, relevance_score)
VALUES
('contact-002', 'Michael Torres', 'Chief Scientific Officer', 'ProtaGene Therapeutics', 'CA', 'https://linkedin.com/in/michaeltorres', '2nd', 9.5);
INSERT OR IGNORE INTO linkedin_contacts (source_id, name, title, company, company_state, linkedin_url, connection_degree, relevance_score)
VALUES
('contact-003', 'Jennifer Park', 'Head of Preclinical Development', 'CellVantage Therapeutics', 'NJ', 'https://linkedin.com/in/jenniferpark', '3rd', 9.0);
INSERT OR IGNORE INTO linkedin_contacts (source_id, name, title, company, company_state, linkedin_url, connection_degree, relevance_score)
VALUES
('contact-004', 'David Kim', 'Director of Toxicology', 'Repertoire Immune Medicines', 'MA', 'https://linkedin.com/in/davidkim', '2nd', 8.8);
INSERT OR IGNORE INTO linkedin_contacts (source_id, name, title, company, company_state, linkedin_url, connection_degree, relevance_score)
VALUES
('contact-005', 'Rachel Gupta', 'SVP Discovery', 'Adlai Nortye Biopharma', 'NY', 'https://linkedin.com/in/rachelgupta', '3rd', 8.6);
INSERT OR IGNORE INTO linkedin_contacts (source_id, name, title, company, company_state, linkedin_url, connection_degree, relevance_score)
VALUES
('contact-006', 'Thomas Wright', 'VP Chemistry', 'Aureka Biotech', 'CA', 'https://linkedin.com/in/thomaswright', '2nd', 7.8);
INSERT OR IGNORE INTO linkedin_contacts (source_id, name, title, company, company_state, linkedin_url, connection_degree, relevance_score)
VALUES
('contact-007', 'Anna Lindström', 'CEO', 'Nordic BioAnalytics', 'MA', 'https://linkedin.com/in/annalindstrom', '2nd', 7.5);
INSERT OR IGNORE INTO linkedin_contacts (source_id, name, title, company, company_state, linkedin_url, connection_degree, relevance_score)
VALUES
('contact-008', 'Robert Chang', 'Head of Outsourcing', 'GenEdit Therapeutics', 'CA', 'https://linkedin.com/in/robertchang', '2nd', 9.8);
INSERT OR IGNORE INTO linkedin_contacts (source_id, name, title, company, company_state, linkedin_url, connection_degree, relevance_score)
VALUES
('contact-009', 'Lisa Park', 'Director CMC', 'ImmunoCore Biologics', 'MD', 'https://linkedin.com/in/lisapark', '3rd', 7.6);
INSERT OR IGNORE INTO linkedin_contacts (source_id, name, title, company, company_state, linkedin_url, connection_degree, relevance_score)
VALUES
('contact-010', 'Kevin Zhao', 'VP Pharmacology', 'Atlas Venture (stealth biotech)', 'MA', 'https://linkedin.com/in/kevinzhao', '3rd', 8.2);
INSERT OR IGNORE INTO linkedin_contacts (source_id, name, title, company, company_state, linkedin_url, connection_degree, relevance_score)
VALUES
('contact-011', 'Daniel Fischer', 'CRO Alliance Manager', 'Novartis', 'MA', 'https://linkedin.com/in/danielfischer', '2nd', 7.0);
INSERT OR IGNORE INTO linkedin_contacts (source_id, name, title, company, company_state, linkedin_url, connection_degree, relevance_score)
VALUES
('contact-012', 'Nicole Brooks', 'Director of Biology', 'Beam Therapeutics', 'MA', 'https://linkedin.com/in/nicolebrooks', '2nd', 7.5);
INSERT OR IGNORE INTO linkedin_contacts (source_id, name, title, company, company_state, linkedin_url, connection_degree, relevance_score)
VALUES
('contact-013', 'Hannah Chen', 'Head of Bioanalysis', 'EQRx', 'MA', 'https://linkedin.com/in/hannahchen', '3rd', 7.8);
INSERT OR IGNORE INTO linkedin_contacts (source_id, name, title, company, company_state, linkedin_url, connection_degree, relevance_score)
VALUES
('contact-014', 'Sebastian Mueller', 'VP Drug Safety', 'BioNTech', 'PA', 'https://linkedin.com/in/sebastianmueller', '2nd', 7.2);
INSERT OR IGNORE INTO linkedin_contacts (source_id, name, title, company, company_state, linkedin_url, connection_degree, relevance_score)
VALUES
('contact-015', 'Raj Patel', 'Head of DMPK', 'Kura Oncology', 'CA', 'https://linkedin.com/in/rajpatel', '2nd', 8.0);
INSERT OR IGNORE INTO linkedin_contacts (source_id, name, title, company, company_state, linkedin_url, connection_degree, relevance_score)
VALUES
('contact-016', 'Jason Wu', 'CEO', 'Enlaza Therapeutics', 'CA', 'https://linkedin.com/in/jasonwu', '2nd', 8.5);
INSERT OR IGNORE INTO linkedin_contacts (source_id, name, title, company, company_state, linkedin_url, connection_degree, relevance_score)
VALUES
('contact-017', 'Mia Johansson', 'Director of Outsourcing', 'ORIC Pharmaceuticals', 'CA', 'https://linkedin.com/in/miajohansson', '2nd', 8.3);
INSERT OR IGNORE INTO linkedin_contacts (source_id, name, title, company, company_state, linkedin_url, connection_degree, relevance_score)
VALUES
('contact-018', 'Chris Henderson', 'VP Manufacturing', 'Arcellx', 'MD', 'https://linkedin.com/in/chrishenderson', '3rd', 7.0);
INSERT OR IGNORE INTO linkedin_contacts (source_id, name, title, company, company_state, linkedin_url, connection_degree, relevance_score)
VALUES
('contact-019', 'Linda Zhou', 'Toxicology Director', 'Blueprint Medicines', 'MA', 'https://linkedin.com/in/lindazhou', '2nd', 7.5);
INSERT OR IGNORE INTO linkedin_contacts (source_id, name, title, company, company_state, linkedin_url, connection_degree, relevance_score)
VALUES
('contact-020', 'Marcus Lee', 'CEO', 'Totus Medicines', 'MA', 'https://linkedin.com/in/marcuslee', '3rd', 8.8);
INSERT OR IGNORE INTO linkedin_contacts (source_id, name, title, company, company_state, linkedin_url, connection_degree, relevance_score)
VALUES
('contact-021', 'Michelle Carter', 'Director of Preclinical', 'Magnet Biomedicine', 'MA', 'https://linkedin.com/in/michellecarter', '2nd', 8.2);
INSERT OR IGNORE INTO linkedin_contacts (source_id, name, title, company, company_state, linkedin_url, connection_degree, relevance_score)
VALUES
('contact-022', 'Ryan Nakamura', 'Head of CMC Strategy', 'Kymera Therapeutics', 'MA', 'https://linkedin.com/in/ryannakamura', '3rd', 7.5);
INSERT OR IGNORE INTO linkedin_contacts (source_id, name, title, company, company_state, linkedin_url, connection_degree, relevance_score)
VALUES
('contact-023', 'Helena Bergström', 'VP Translational Medicine', 'Werewolf Therapeutics', 'MA', 'https://linkedin.com/in/helenabergstrom', '2nd', 7.8);
INSERT OR IGNORE INTO linkedin_contacts (source_id, name, title, company, company_state, linkedin_url, connection_degree, relevance_score)
VALUES
('contact-024', 'Paul Andersen', 'CEO', 'Apogee Therapeutics', 'MA', 'https://linkedin.com/in/paulandersen', '2nd', 9.0);
INSERT OR IGNORE INTO linkedin_contacts (source_id, name, title, company, company_state, linkedin_url, connection_degree, relevance_score)
VALUES
('contact-025', 'Daniel Ortega', 'VP Clinical Pharmacology', 'Arvinas', 'CT', 'https://linkedin.com/in/danielortega', '2nd', 8.5);
INSERT OR IGNORE INTO linkedin_contacts (source_id, name, title, company, company_state, linkedin_url, connection_degree, relevance_score)
VALUES
('contact-026', 'Cynthia Zhao', 'SVP Preclinical', 'Janux Therapeutics', 'CA', 'https://linkedin.com/in/cynthiazhao', '3rd', 7.8);
INSERT OR IGNORE INTO linkedin_contacts (source_id, name, title, company, company_state, linkedin_url, connection_degree, relevance_score)
VALUES
('contact-027', 'Brandon Hayes', 'CEO', 'Odyssey Therapeutics', 'MA', 'https://linkedin.com/in/brandonhayes', '2nd', 9.5);
INSERT OR IGNORE INTO linkedin_contacts (source_id, name, title, company, company_state, linkedin_url, connection_degree, relevance_score)
VALUES
('contact-028', 'Emily Watson', 'Senior Director Biologics', 'AstraZeneca', 'MD', 'https://linkedin.com/in/emilywatson', '3rd', 6.5);
INSERT OR IGNORE INTO linkedin_contacts (source_id, name, title, company, company_state, linkedin_url, connection_degree, relevance_score)
VALUES
('contact-029', 'Omar Hassan', 'VP Business Development', 'WuXi AppTec', 'NJ', 'https://linkedin.com/in/omarhassan', '2nd', 6.0);
INSERT OR IGNORE INTO linkedin_contacts (source_id, name, title, company, company_state, linkedin_url, connection_degree, relevance_score)
VALUES
('contact-030', 'Andrew Kim', 'Sr. Director Discovery', 'Relay Therapeutics', 'MA', 'https://linkedin.com/in/andrewkim', '2nd', 7.2);
INSERT OR IGNORE INTO linkedin_contacts (source_id, name, title, company, company_state, linkedin_url, connection_degree, relevance_score)
VALUES
('contact-031', 'Tanya Williams', 'Associate Director Bioanalysis', 'Agios Pharmaceuticals', 'MA', 'https://linkedin.com/in/tanyawilliams', '3rd', 7.5);
INSERT OR IGNORE INTO linkedin_contacts (source_id, name, title, company, company_state, linkedin_url, connection_degree, relevance_score)
VALUES
('contact-032', 'Tom Bradley', 'Business Development', 'Labcorp Drug Development', 'NC', 'https://linkedin.com/in/tombradley', '2nd', 5.5);
INSERT OR IGNORE INTO linkedin_contacts (source_id, name, title, company, company_state, linkedin_url, connection_degree, relevance_score)
VALUES
('contact-033', 'Brian Mitchell', 'VP Sales', 'Charles River Laboratories', 'MA', 'https://linkedin.com/in/brianmitchell', '2nd', 5.2);
INSERT OR IGNORE INTO linkedin_contacts (source_id, name, title, company, company_state, linkedin_url, connection_degree, relevance_score)
VALUES
('contact-034', 'Vanessa Moore', 'Drug Discovery Scientist', 'Amgen', 'CA', 'https://linkedin.com/in/vanessamoore', '3rd', 5.0);
INSERT OR IGNORE INTO linkedin_contacts (source_id, name, title, company, company_state, linkedin_url, connection_degree, relevance_score)
VALUES
('contact-035', 'Diana Torres', 'Head of Regulatory', 'Intellia Therapeutics', 'MA', 'https://linkedin.com/in/dianatorres', '2nd', 6.8);
INSERT OR IGNORE INTO linkedin_contacts (source_id, name, title, company, company_state, linkedin_url, connection_degree, relevance_score)
VALUES
('contact-036', 'Naveen Krishnan', 'CMC Project Manager', 'FogPharma', 'MA', 'https://linkedin.com/in/naveenkrishnan', '3rd', 6.5);
INSERT OR IGNORE INTO linkedin_contacts (source_id, name, title, company, company_state, linkedin_url, connection_degree, relevance_score)
VALUES
('contact-037', 'Sophie Martin', 'Bioanalytical Lead', 'C4 Therapeutics', 'MA', 'https://linkedin.com/in/sophiemartin', '2nd', 7.0);
INSERT OR IGNORE INTO linkedin_contacts (source_id, name, title, company, company_state, linkedin_url, connection_degree, relevance_score)
VALUES
('contact-038', 'Rachel Lee', 'Director of Operations', 'Seismic Therapeutic', 'MA', 'https://linkedin.com/in/rachellee', '3rd', 6.5);
INSERT OR IGNORE INTO linkedin_contacts (source_id, name, title, company, company_state, linkedin_url, connection_degree, relevance_score)
VALUES
('contact-039', 'Oliver Schmidt', 'Head of Toxicology', 'Bayer Pharmaceuticals', 'NJ', 'https://linkedin.com/in/oliverschmidt', '3rd', 6.2);
INSERT OR IGNORE INTO linkedin_contacts (source_id, name, title, company, company_state, linkedin_url, connection_degree, relevance_score)
VALUES
('contact-040', 'Mark Fisher', 'Investor', 'OrbiMed Advisors', 'NY', 'https://linkedin.com/in/markfisher', '2nd', 5.8);
