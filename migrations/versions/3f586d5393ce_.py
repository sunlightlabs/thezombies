"""empty message

Revision ID: 3f586d5393ce
Revises: None
Create Date: 2014-08-23 20:03:26.675876

"""

# revision identifiers, used by Alembic.
revision = '3f586d5393ce'
down_revision = None

from alembic import op, context
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade():
    op.create_table('agency',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=True),
    sa.Column('agency_type', sa.String(length=40), nullable=True),
    sa.Column('slug', sa.String(length=120), nullable=True),
    sa.Column('url', sa.String(length=200), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name'),
    sa.UniqueConstraint('slug'),
    sa.UniqueConstraint('url')
    )
    op.create_table('report',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('agency_id', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('url', sa.String(length=200), nullable=True),
    sa.Column('message', sa.Text(), nullable=True),
    sa.Column('data', postgresql.HSTORE(), nullable=True),
    sa.ForeignKeyConstraint(['agency_id'], ['agency.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    data_upgrades()


def downgrade():
    op.drop_table('report')
    op.drop_table('agency')

def data_upgrades():
    agency_table = sa.sql.table('agency',
        sa.sql.column('id', sa.Integer),
        sa.sql.column('name', sa.String),
        sa.sql.column('agency_type', sa.String),
        sa.sql.column('slug', sa.String),
        sa.sql.column('url', sa.String),
    )

    op.bulk_insert(agency_table,
        [
            {
                "url": "http://www.usda.gov",
                "agency_type": "Cabinet",
                "name": "Department of Agriculture",
                "id": "1",
                "slug": "department-of-agriculture"
            },
            {
                "url": "http://www.commerce.gov",
                "agency_type": "Cabinet",
                "name": "Department of Commerce",
                "id": "2",
                "slug": "department-of-commerce"
            },
            {
                "url": "http://www.defense.gov",
                "agency_type": "Cabinet",
                "name": "Department of Defense",
                "id": "3",
                "slug": "department-of-defense"
            },
            {
                "url": "http://www.ed.gov",
                "agency_type": "Cabinet",
                "name": "Department of Education",
                "id": "4",
                "slug": "department-of-education"
            },
            {
                "url": "http://energy.gov",
                "agency_type": "Cabinet",
                "name": "Department of Energy",
                "id": "5",
                "slug": "department-of-energy"
            },
            {
                "url": "http://www.hhs.gov",
                "agency_type": "Cabinet",
                "name": "Department of Health and Human Services",
                "id": "6",
                "slug": "department-of-health-and-human-services"
            },
            {
                "url": "http://www.dhs.gov",
                "agency_type": "Cabinet",
                "name": "Department of Homeland Security",
                "id": "7",
                "slug": "department-of-homeland-security"
            },
            {
                "url": "http://www.hud.gov",
                "agency_type": "Cabinet",
                "name": "Department of Housing and Urban Development",
                "id": "8",
                "slug": "department-of-housing-and-urban-development"
            },
            {
                "url": "http://www.justice.gov",
                "agency_type": "Cabinet",
                "name": "Department of Justice",
                "id": "9",
                "slug": "department-of-justice"
            },
            {
                "url": "http://www.dol.gov",
                "agency_type": "Cabinet",
                "name": "Department of Labor",
                "id": "10",
                "slug": "department-of-labor"
            },
            {
                "url": "http://www.state.gov",
                "agency_type": "Cabinet",
                "name": "Department of State",
                "id": "11",
                "slug": "department-of-state"
            },
            {
                "url": "http://interior.gov",
                "agency_type": "Cabinet",
                "name": "Department of the Interior",
                "id": "12",
                "slug": "department-of-the-interior"
            },
            {
                "url": "http://www.treasury.gov",
                "agency_type": "Cabinet",
                "name": "Department of the Treasury",
                "id": "13",
                "slug": "department-of-the-treasury"
            },
            {
                "url": "http://www.dot.gov",
                "agency_type": "Cabinet",
                "name": "Department of Transportation",
                "id": "14",
                "slug": "department-of-transportation"
            },
            {
                "url": "http://www.va.gov",
                "agency_type": "Cabinet",
                "name": "Department of Veterans Affairs",
                "id": "15",
                "slug": "department-of-veterans-affairs"
            },
            {
                "url": "http://gsa.gov",
                "agency_type": "Independent",
                "name": "General Services Administration",
                "id": "16",
                "slug": "general-services-administration"
            },
            {
                "url": "http://www.epa.gov",
                "agency_type": "Independent",
                "name": "Environmental Protection Agency",
                "id": "17",
                "slug": "environmental-protection-agency"
            },
            {
                "url": "http://www.usaid.gov",
                "agency_type": "Independent",
                "name": "USAID",
                "id": "18",
                "slug": "usaid"
            },
            {
                "url": "http://www.ssa.gov",
                "agency_type": "Independent",
                "name": "Social Security Administration",
                "id": "19",
                "slug": "social-security-administration"
            },
            {
                "url": "http://www.sec.gov",
                "agency_type": "Independent",
                "name": "Securities and Exchange Commission",
                "id": "20",
                "slug": "securities-and-exchange-commission"
            },
            {
                "url": "http://www.opm.gov",
                "agency_type": "Independent",
                "name": "Office of Personnel Management",
                "id": "21",
                "slug": "office-of-personnel-management"
            },
            {
                "url": "http://www.nrc.gov",
                "agency_type": "Independent",
                "name": "Nuclear Regulatory Commission",
                "id": "22",
                "slug": "nuclear-regulatory-commission"
            },
            {
                "url": "http://www.ntsb.gov",
                "agency_type": "Independent",
                "name": "National Transportation Safety Board",
                "id": "23",
                "slug": "national-transportation-safety-board"
            },
            {
                "url": "http://www.nsf.gov",
                "agency_type": "Independent",
                "name": "National Science Foundation",
                "id": "24",
                "slug": "national-science-foundation"
            },
            {
                "url": "http://www.archives.gov",
                "agency_type": "Independent",
                "name": "National Archives",
                "id": "25",
                "slug": "national-archives"
            },
            {
                "url": "http://www.imls.gov",
                "agency_type": "Independent",
                "name": "Institute of Museum and Library Services",
                "id": "26",
                "slug": "institute-of-museum-and-library-services"
            },
            {
                "url": "http://www.consumerfinance.gov",
                "agency_type": "Independent",
                "name": "Consumer Financial Protection Bureau",
                "id": "27",
                "slug": "consumer-financial-protection-bureau-"
            },
            {
                "url": "http://www.nationalservice.gov",
                "agency_type": "Independent",
                "name": "Corporation for National and Community Service",
                "id": "28",
                "slug": "corporation-for-national-and-community-service"
            },
            {
                "url": "http://www.fcc.gov",
                "agency_type": "Independent",
                "name": "Federal Communications Commission",
                "id": "29",
                "slug": "federal-communications-commission"
            },
            {
                "url": "http://www.fhfa.gov",
                "agency_type": "Independent",
                "name": "Federal Housing Finance Agency",
                "id": "30",
                "slug": "federal-housing-finance-agency"
            },
            {
                "url": "http://www.mcc.gov",
                "agency_type": "Independent",
                "name": "Millenium Challenge Corporation",
                "id": "31",
                "slug": "millenium-challenge-corporation"
            },
            {
                "url": "http://www.nasa.gov",
                "agency_type": "Independent",
                "name": "National Aeronautics and Space Administration",
                "id": "32",
                "slug": "national-aeronautics-and-space-administration"
            },
            {
                "url": "http://rrb.gov",
                "agency_type": "Independent",
                "name": "Railroad Retirement Board",
                "id": "33",
                "slug": "railroad-retirement-board"
            },
            {
                "url": "http://www.sba.gov",
                "agency_type": "Independent",
                "name": "Small Business Administration",
                "id": "34",
                "slug": "small-business-administration"
            },
            {
                "url": "http://www.peacecorps.gov",
                "agency_type": "Independent",
                "name": "Peace Corps",
                "id": "35",
                "slug": "peace-corps"
            }
        ]
    )
