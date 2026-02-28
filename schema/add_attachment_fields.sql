-- Add attachment fields to emails table
DO $$ 
BEGIN
    -- Add attachment_file_path if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='emails' AND column_name='attachment_file_path') THEN
        ALTER TABLE emails ADD COLUMN attachment_file_path TEXT;
        RAISE NOTICE 'Added attachment_file_path column';
    ELSE
        RAISE NOTICE 'attachment_file_path column already exists';
    END IF;
    
    -- Add attachment_image_path if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='emails' AND column_name='attachment_image_path') THEN
        ALTER TABLE emails ADD COLUMN attachment_image_path TEXT;
        RAISE NOTICE 'Added attachment_image_path column';
    ELSE
        RAISE NOTICE 'attachment_image_path column already exists';
    END IF;
END $$;

-- Create indexes for attachment paths
CREATE INDEX IF NOT EXISTS idx_emails_attachment_file ON emails(attachment_file_path) WHERE attachment_file_path IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_emails_attachment_image ON emails(attachment_image_path) WHERE attachment_image_path IS NOT NULL;

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'Attachment fields added successfully!';
END $$;
