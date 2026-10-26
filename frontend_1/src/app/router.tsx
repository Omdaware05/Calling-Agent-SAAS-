import React from 'react';
import { createBrowserRouter, Navigate } from 'react-router-dom';
import { AppShell } from '../components/layout/AppShell';

// Features & Pages
import { DashboardPage } from '../features/dashboard/DashboardPage';
import { BusinessesPage } from '../features/businesses/BusinessesPage';
import { BusinessDetailPage } from '../features/businesses/BusinessDetailPage';
import { CallsPage } from '../features/calls/CallsPage';
import { ActiveCallsPage } from '../features/calls/ActiveCallsPage';
import { QueuePage } from '../features/calls/QueuePage';
import { AgentsPage } from '../features/agents/AgentsPage';
import { AgentWorkspacePage } from '../features/agents/AgentWorkspacePage';
import { QuestionnairesPage } from '../features/questionnaires/QuestionnairesPage';
import { QuestionnaireEditorPage } from '../features/questionnaires/QuestionnaireEditorPage';
import { CampaignsPage } from '../features/campaigns/CampaignsPage';
import { ContactsPage } from '../features/contacts/ContactsPage';
import { LeadsPage } from '../features/leads/LeadsPage';
import { FollowupsPage } from '../features/followups/FollowupsPage';
import { ReportsPage } from '../features/reports/ReportsPage';
import { InvoicesPage } from '../features/invoices/InvoicesPage';
import { ModelConfigPage } from '../features/models/ModelConfigPage';
import { ModelLabPage } from '../features/model_lab/ModelLabPage';
import { HealthPage } from '../features/health/HealthPage';
import { SettingsPage } from '../features/settings/SettingsPage';

export const router = createBrowserRouter([
  {
    path: '/',
    element: <AppShell />,
    children: [
      { index: true, element: <DashboardPage /> },
      { path: 'businesses', element: <BusinessesPage /> },
      { path: 'businesses/:id', element: <BusinessDetailPage /> },
      { path: 'calls', element: <CallsPage /> },
      { path: 'active-calls', element: <ActiveCallsPage /> },
      { path: 'queue', element: <QueuePage /> },
      { path: 'model-lab', element: <ModelLabPage /> },
      { path: 'agents', element: <AgentsPage /> },
      { path: 'agents/:id', element: <AgentWorkspacePage /> },
      { path: 'questionnaires', element: <QuestionnairesPage /> },
      { path: 'questionnaires/:id', element: <QuestionnaireEditorPage /> },
      { path: 'campaigns', element: <CampaignsPage /> },
      { path: 'contacts', element: <ContactsPage /> },
      { path: 'leads', element: <LeadsPage /> },
      { path: 'followups', element: <FollowupsPage /> },
      { path: 'reports', element: <ReportsPage /> },
      { path: 'invoices', element: <InvoicesPage /> },
      { path: 'settings/models', element: <ModelConfigPage /> },
      { path: 'settings/health', element: <HealthPage /> },
      { path: 'settings/telephony', element: <SettingsPage initialTab="telephony" /> },
      { path: 'settings/transcript', element: <SettingsPage initialTab="transcript" /> },
      { path: 'settings', element: <SettingsPage /> },
      { path: '*', element: <Navigate to="/" replace /> },
    ],
  },
]);
